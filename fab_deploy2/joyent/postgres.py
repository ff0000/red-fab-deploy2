import os
import sys
import time
import tempfile

from fabric.api import run, sudo, env, local, hide, settings
from fabric.contrib.files import append, sed, exists, contains
from fabric.context_managers import prefix
from fabric.operations import get, put
from fabric.context_managers import cd

from fabric.tasks import Task

from fab_deploy2.functions import random_password
from fab_deploy2.base import postgres as base_postgres

class JoyentMixin(object):
    version_directory_join = ''

    def _get_data_dir(self, db_version):
        # Try to get from svc first
        output = run('svcprop -p config/data postgresql')
        if output.stdout and exists(output.stdout, use_sudo=True):
            return output.stdout
        return base_postgres.PostgresInstall._get_data_dir(self, db_version)

    def _install_package(self, db_version):
        sudo("pkg_add postgresql%s-server" %db_version)
        sudo("pkg_add postgresql%s-replicationtools" %db_version)
        sudo("svcadm enable postgresql")

    def _restart_db_server(self, db_version):
        sudo('svcadm restart postgresql')

    def _stop_db_server(self, db_version):
        sudo('svcadm disable postgresql')

    def _start_db_server(self, db_version):
        sudo('svcadm enable postgresql')

class PostgresInstall(JoyentMixin, base_postgres.PostgresInstall):
    """
    Install postgresql on server

    install postgresql package;
    enable postgres access from localhost without password;
    enable all other user access from other machines with password;
    setup a few parameters related with streaming replication;
    database server listen to all machines '*';
    create a user for database with password.
    """

    name = 'master_setup'
    db_version = '9.1'

class SlaveSetup(JoyentMixin, base_postgres.SlaveSetup):
    """
    Set up master-slave streaming replication: slave node
    """

    name = 'slave_setup'


class PGBouncerInstall(Task):
    """
    Set up PGBouncer on a database server
    """

    name = 'setup_pgbouncer'

    config_dir = '/etc/opt/pkg'
    pkg_name = 'pgbouncer'

    config = {
        '*':              'host=127.0.0.1',
        'logfile':        '/var/log/pgbouncer/pgbouncer.log',
        'listen_addr':    '*',
        'listen_port':    '6432',
        'unix_socket_dir': '/tmp',
        'auth_type':      'md5',
        'auth_file':      '%s/pgbouncer.userlist' %config_dir,
        'pool_mode':      'session',
        'admin_users':    'postgres',
        'stats_users':    'postgres',
        }

    def install_package(self):
        sudo('pkg_add %s' %self.pkg_name)

    def _setup_parameter(self, file_name, **kwargs):
        for key, value in kwargs.items():
            origin = "%s =" %key
            new = "%s = %s" %(key, value)
            sudo('sed -i "/%s/ c\%s" %s' %(origin, new, file_name))

    def _get_passwd(self, username):
        with hide('output'):
            string = run('echo "select usename, passwd from pg_shadow where '
                         'usename=\'%s\' order by 1" | sudo su postgres -c '
                         '"psql"' %username)

        user, passwd = string.split('\n')[2].split('|')
        user = user.strip()
        passwd = passwd.strip()

        __, tmp_name = tempfile.mkstemp()
        fn = open(tmp_name, 'w')
        fn.write('"%s" "%s" ""\n' %(user, passwd))
        fn.close()
        put(tmp_name, '%s/pgbouncer.userlist'%self.config_dir, use_sudo=True)
        local('rm %s' %tmp_name)

    def _get_username(self, section=None):
        try:
            names = env.config_object.get_list(section, env.config_object.USERNAME)
            username = names[0]
        except:
            print ('You must first set up a database server on this machine, '
                   'and create a database user')
            raise
        return username

    def run(self, section=None):
        """
        """

        sudo('mkdir -p /opt/pkg/bin')
        sudo("ln -sf /opt/local/bin/awk /opt/pkg/bin/nawk")
        sudo("ln -sf /opt/local/bin/sed /opt/pkg/bin/nbsed")

        self.install_package()

        home = run('bash -c "echo ~postgres"')
        bounce_home = os.path.join(home, 'pgbouncer')

        pidfile = os.path.join(bounce_home, 'pgbouncer.pid')
        self._setup_parameter('%s/pgbouncer.ini' %self.config_dir,
                              pidfile=pidfile, **self.config)

        if not section:
            section = 'db-server'
        username = self._get_username(section)
        self._get_passwd(username)
        # postgres should be the owner of these config files
        sudo('chown -R postgres:postgres %s' %self.config_dir)

        sudo('mkdir -p %s' % bounce_home)
        sudo('chown postgres:postgres %s' % bounce_home)

        sudo('mkdir -p /var/log/pgbouncer')
        sudo('chown postgres:postgres /var/log/pgbouncer')

        # set up log
        sudo('logadm -C 3 -p1d -c -w /var/log/pgbouncer/pgbouncer.log -z 1')

        # start pgbouncer
        sudo('svcadm enable pgbouncer')


class PostGISInstall(Task):
    """
    Set up PostGIS template for use on database server.
    """

    name = 'setup_postgis'

    def install_package(self):
        sudo("pkg_add postgresql91-postgis")
        with settings(warn_only=True):
            sudo("pkgin in posgresql91-postgis1.5.3nb5")
        sudo("svcadm restart postgresql")


    def setup_postgis_template(self):
        POSTGIS_SQL_PATH = "/opt/local/share/postgresql/contrib/postgis-1.5"
        run("sudo su postgres -c 'createdb -E UTF8 template_postgis'")
        run("sudo su postgres -c 'createlang -d template_postgis plpgsql'")
        run("sudo su postgres -c 'psql -d postgres -c \"UPDATE pg_database SET datistemplate='\\''true'\\'' WHERE datname='\\''template_postgis'\\'';\"'")
        run("sudo su postgres -c 'psql -d template_postgis -f %s/postgis.sql'" % POSTGIS_SQL_PATH)
        run("sudo su postgres -c 'psql -d template_postgis -f %s/spatial_ref_sys.sql'" % POSTGIS_SQL_PATH)
        run("sudo su postgres -c 'psql -d template_postgis -c \"GRANT ALL ON geometry_columns TO PUBLIC;\"'")
        run("sudo su postgres -c 'psql -d template_postgis -c \"GRANT ALL ON geography_columns TO PUBLIC;\"'")
        run("sudo su postgres -c 'psql -d template_postgis -c \"GRANT ALL ON spatial_ref_sys TO PUBLIC;\"'")     


    def run(self):
        self.install_package()
        time.sleep(5) # sleeping to avoid trying to connect to a database that hasn't restarted
        self.setup_postgis_template()


setup = PostgresInstall()
slave_setup = SlaveSetup()
setup_pgbouncer = PGBouncerInstall()
setup_backup = base_postgres.Backups()
setup_postgis = PostGISInstall()
