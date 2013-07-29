import os

from fab_deploy2 import functions
from fab_deploy2.config import CustomConfig
from fab_deploy2.base import snmp as base_snmp

from fabric.api import run, sudo, env, put, execute, local
from fabric.tasks import Task

class SNMPSetup(base_snmp.SNMPSetup):
    """
    Setup snmp
    """

    remote_config_path = '/opt/local/etc/snmpd.conf'
    name = 'setup'

    def _add_package(self):
        sudo("mkdir -p /var/net-snmp/mib_indexes")
        sudo("pkg_add net-snmp")
        run('svcadm enable snmp')

    def _restart_service(self):
        run('svcadm restart snmp')


setup = SNMPSetup()
