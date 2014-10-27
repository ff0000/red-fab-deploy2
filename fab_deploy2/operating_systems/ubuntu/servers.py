from fabric.api import sudo

from fab_deploy2.base import servers as base_servers
from . import platform as base_platform

class UbuntuMixin(object):
    serial = True
    setup_firewall = False
    setup_snmp = False
    platform = base_platform

    def _ssh_restart(self):
        sudo('apt-get update')
        sudo('service ssh restart')

class AppMixin(UbuntuMixin):
    packages = ['python-psycopg2', 'python-setuptools', 'python-imaging',
                'python-pip']

class AppServer(AppMixin, base_servers.AppServer):

    def _modify_others(self):
        pass

class DBServer(UbuntuMixin, base_servers.DBServer):
    pass

class DBSlaveServer(UbuntuMixin, base_servers.DBSlaveServer):
    pass

class DevServer(AppMixin, base_servers.DevServer):
    pass

AppServer().as_tasks(name="app_server")
DBServer().as_tasks(name="db_server")
DBSlaveServer().as_tasks(name="slave_server")
DevServer().as_tasks(name="dev_server")
