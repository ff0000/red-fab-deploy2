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

    remote_config_path = '/etc/snmp/snmpd.conf'
    name = 'setup'

    def _add_package(self):
        sudo('sed -i "/^# deb.*multiverse/ s/^# //" /etc/apt/sources.list')
        sudo("apt-get update")
        sudo("apt-get install -y snmpd")
        sudo("apt-get install -y snmp-mibs-downloader")
        sudo('echo "" > /etc/snmp/snmp.conf')
        sudo('service snmpd start')

    def _restart_service(self):
        sudo('service snmpd restart')


setup = SNMPSetup()
