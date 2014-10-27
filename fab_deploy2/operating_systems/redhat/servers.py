from fabric.api import sudo

from fab_deploy2.base import servers as base_servers
from . import platform as base_platform

class RHMixin(object):
    serial = True
    setup_firewall = False
    setup_snmp = False
    platform = base_platform

    def _ssh_restart(self):
        sudo('service sshd restart')


class AppMixin(RHMixin):
    packages = ['python-psycopg2', 'python-setuptools', 'python-imaging',
                'python-pip']


class AppServer(AppMixin, base_servers.AppServer):

    def get_context(self):
        assert False

class DBServer(RHMixin, base_servers.DBServer):
    pass


class DBSlaveServer(RHMixin, base_servers.DBSlaveServer):
    pass


class DevServer(AppMixin, base_servers.DevServer):
    pass


AppServer().as_tasks(name="app_server")
DBServer().as_tasks(name="db_server")
DBSlaveServer().as_tasks(name="slave_server")
DevServer().as_tasks(name="dev_server")
