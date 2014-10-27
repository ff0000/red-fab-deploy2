import os

from fab_deploy2.base import nginx as base_nginx
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, local
from fabric.tasks import Task

class Nginx(base_nginx.Nginx):
    """
    Install nginx
    """

    def _install_package(self):
        functions.execute_on_host('utils.install_package', package_name='nginx')

    def _setup_logging(self):
        sudo('sed -ie "s/^#nginx\(.*\)/nginx\\1/g" /etc/logadm.conf')
        sudo('logadm')

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name='nginx',
                host=[env.host_string])

    @task_method
    def stop(self):
        run('svcadm disable nginx')

Nginx().as_tasks()
