import os
import tempfile

from fabric.api import run, sudo, env, local, hide
from fabric.operations import put
from fabric.tasks import Task
from fabric.contrib.files import exists, append
from fabric.context_managers import settings

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

    binary_path = '/usr/pgsql-9.1/bin/'
    data_dir_default_base = '/var/lib/pgsql'
    version = '9.1'
    package_path = 'http://yum.postgresql.org/9.1/redhat/rhel-6-x86_64/pgdg-redhat91-9.1-5.noarch.rpm'

    def _get_data_dir(self):
        return os.path.join(
            self.data_dir_default_base, '%s' % self.db_version, 'data')

    def _install_package(self):
        pk_version = self.db_version.replace('.', '')
        functions.execute_on_host('utils.install_package',
                                    package_name="postgresql{0}-server".format(pk_version),
                                    remote=self.package_path)
        functions.execute_on_host('utils.install_package',
                                    package_name="postgresql{0}-contrib".format(pk_version))

        postgres_conf = os.path.join(self.config_dir, 'postgresql.conf')
        self._override_pgdata()
        if not exists(postgres_conf, use_sudo=True):
            sudo("service postgresql-%s initdb" % self.db_version)
        sudo('chkconfig postgresql-%s on' % self.db_version)

    def _stop_db_server(self):
        sudo('service postgresql-%s stop' % self.db_version)

    def _start_db_server(self):
        service = "postgresql-{0}".format(self.db_version)
        task = "{0}.start_or_restart_service".format(self.utils)
        functions.execute_on_host(task, service)

    def _override_pgdata(self):
        text = [
            "PGDATA=%s" % self.data_dir,
        ]
        sudo('touch /etc/sysconfig/pgsql/postgresql-%s' % self.db_version)
        append('/etc/sysconfig/pgsql/postgresql-%s' % self.db_version,
                                    text, use_sudo=True)



Postgresql().as_tasks()
