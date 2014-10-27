import os
import tempfile

from fabric.api import run, sudo, env, local, hide
from fabric.operations import put
from fabric.tasks import Task

from fab_deploy2.base import postgres as base_postgres
from fab_deploy2 import functions

class Postgresql(base_postgres.Postgresql):
    """
    Install postgresql on server.

    This task gets executed inside other tasks, including
    setup.db_server, setup.slave_db and setup.dev_server

    install postgresql package, and set up access policy in pg_hba.conf.
    enable postgres access from localhost without password;
    enable all other user access from other machines with password;
    setup a few parameters related with streaming replication;
    database server listen to all machines '*';
    create a user for database with password.
    """

    name = 'master_setup'
    binary_path = '/var/lib/postgresql/bin/'
    version = '9.1'

    def _get_data_dir(self):
        return os.path.join('/var/lib/postgresql', '%s' % self.db_version, 'main')

    def _get_config_dir(self):
        return os.path.join('/etc/postgresql', '%s' % self.db_version, 'main')

    def _install_package(self):
        installed = functions.execute_on_host('utils.install_package', package_name='postgresql')
        if installed:
            sudo('update-rc.d postgresql defaults')
        functions.execute_on_host('utils.install_package', package_name='postgresql-contrib')

    def _stop_db_server(self):
        sudo('service postgresql stop')

    def _start_db_server(self):
        service = "postgresql"
        task = "{0}.start_or_restart_service".format(self.utils)
        functions.execute_on_host(task, service)


class PGBouncerInstall(Task):
    """
    Set up PGBouncer on a database server
    """

    name = 'setup_pgbouncer'

    config_dir = '/etc/pgbouncer'

    config = {
        '*':              'host=127.0.0.1',
        'logfile':        '/var/log/pgbouncer/pgbouncer.log',
        'pidfile':        '/var/run/pgbouncer/pgbouncer.pid',
        'listen_addr':    '*',
        'listen_port':    '6432',
        'unix_socket_dir': '/var/run/postgresql',
        'auth_type':      'md5',
        'auth_file':      '%s/pgbouncer.userlist' % config_dir,
        'pool_mode':      'session',
        'admin_users':    'postgres',
        'stats_users':    'postgres',
        }

    def _setup_parameter(self, file, **kwargs):
        for key, value in kwargs.items():
            origin = "%s =" % key
            new = "%s = %s" % (key, value)
            sudo('sed -i "/%s/ c\%s" %s' % (origin, new, file))

    def _get_passwd(self, username):
        with hide('output'):
            string = run('echo "select usename, passwd from pg_shadow where '
                         'usename=\'%s\' order by 1" | sudo su postgres -c '
                         '"psql"' % username)

        user, passwd = string.split('\n')[2].split('|')
        user = user.strip()
        passwd = passwd.strip()

        __, tmp_name = tempfile.mkstemp()
        fn = open(tmp_name, 'w')
        fn.write('"%s" "%s" ""\n' % (user, passwd))
        fn.close()
        put(tmp_name, '%s/pgbouncer.userlist' % self.config_dir, use_sudo=True)
        local('rm %s' % tmp_name)

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
        functions.execute_on_host('utils.install_package', package_name='pgbouncer')

        self._setup_parameter('%s/pgbouncer.ini' % self.config_dir, **self.config)

        if not section:
            section = 'db-server'
        username = self._get_username(section)
        self._get_passwd(username)
        # postgres should be the owner of these config files
        sudo('chown -R postgres:postgres %s' % self.config_dir)

        # pgbouncer won't run smoothly without these directories
        sudo('mkdir -p /var/run/pgbouncer')
        sudo('mkdir -p /var/log/pgbouncer')
        sudo('chown postgres:postgres /var/run/pgbouncer')
        sudo('chown postgres:postgres /var/log/pgbouncer')

        # start pgbouncer
        pgbouncer_control_file = '/etc/default/pgbouncer'
        sudo("sed -i 's/START=0/START=1/' %s" %pgbouncer_control_file)
        sudo('service pgbouncer start')

Postgresql().as_tasks()
setup_pgbouncer = PGBouncerInstall()
