import os

from fab_deploy2 import functions
from fab_deploy2.config import CustomConfig
from fab_deploy2.base import snmp as base_snmp

from fabric.api import run, sudo, env, put, local
from fabric.tasks import Task

class SNMPSetup(base_snmp.SNMPSetup):
    """
    Setup snmp
    """

    remote_config_path = '/etc/snmp/snmpd.conf'
    name = 'setup'

    def _add_package(self):

        installed = functions.execute_on_host('utils.install_package', package_name='snmpd')
        if installed:
            sudo('sed -i "/^# deb.*multiverse/ s/^# //" /etc/apt/sources.list')
            functions.execute_on_host('utils.install_package',
                                package_name='snmp-mibs-downloader', update=True)
            sudo('update-rc.d snmpd defaults')

        sudo('echo "" > {0}'.format(self.remote_config_path))
        sudo('service snmpd start')


    def _restart_service(self):
        sudo('service snmpd restart')


setup = SNMPSetup()
