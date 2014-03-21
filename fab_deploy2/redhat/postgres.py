import os
import tempfile

from fabric.api import run, sudo, env, local, hide
from fabric.operations import put
from fabric.tasks import Task
from fabric.contrib.files import exists, append
from fabric.context_managers import settings

from fab_deploy2.base import postgres as base_postgres


class RHMixin(object):
    binary_path = '/usr/pgsql-9.1/bin/'
    data_dir_default_base = '/var/lib/pgsql'

    def _get_data_dir(self, db_version):
        return os.path.join(
            self.data_dir_default_base, '%s' % db_version, 'data')

    def _install_package(self, db_version):
        sudo("rpm -U --replacepkgs http://yum.postgresql.org/9.1/redhat/rhel-6-x86_64/pgdg-redhat91-9.1-5.noarch.rpm")
        pk_version = db_version.replace('.', '')
        sudo("yum -y install postgresql%s-server" % pk_version)
        sudo("yum -y install postgresql%s-contrib" % pk_version)
        data_dir = self._get_data_dir(db_version)
        postgres_conf = os.path.join(
            self._get_config_dir(db_version, data_dir),
            'postgresql.conf')
        self._override_pgdata(db_version)
        if not exists(postgres_conf, use_sudo=True):
            sudo("service postgresql-%s initdb" % db_version)

    def _restart_db_server(self, db_version):
        with settings(warn=True):
            sudo('service postgresql-%s restart' % db_version)

    def _stop_db_server(self, db_version):
        sudo('service postgresql-%s stop' % db_version)

    def _start_db_server(self, db_version):
        sudo('service postgresql-%s start' % db_version)

    def _override_pgdata(self, db_version):
        text = [
            "PGDATA=%s" % self._get_data_dir(db_version),
        ]
        sudo('touch /etc/sysconfig/pgsql/postgresql-%s' % db_version)
        append('/etc/sysconfig/pgsql/postgresql-%s' % db_version,
                                    text, use_sudo=True)


class PostgresInstall(RHMixin, base_postgres.PostgresInstall):
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
    db_version = '9.1'


class SlaveSetup(RHMixin, base_postgres.SlaveSetup):
    """
    Set up master-slave streaming replication: slave node
    """

    name = 'slave_setup'


class PGBouncerInstall(Task):
    pass


setup = PostgresInstall()
slave_setup = SlaveSetup()
setup_pgbouncer = PGBouncerInstall()
setup_backup = base_postgres.Backups()
