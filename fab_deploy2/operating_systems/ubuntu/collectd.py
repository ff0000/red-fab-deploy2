import os

from fab_deploy2.base import collectd as base_collectd
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, put, local
from fabric.context_managers import settings

class Collectd(base_collectd.Collectd):
    """
    Setup collectd
    """

    name = 'setup'

    def _add_package(self, name):
        installed = functions.execute_on_host('utils.install_package', package_name=name)
        if installed:
            sudo('update-rc.d {0} defaults'.format(name))
        functions.execute_on_host('collectd.start')

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_service', name='collectd')

    @task_method
    def stop(self):
        sudo('service collectd stop')

    def _get_collectd_headers(self):
        functions.execute_on_host('utils.install_package', package_name='collectd-dev')
        return '/usr/include/collectd/'

Collectd().as_tasks()
