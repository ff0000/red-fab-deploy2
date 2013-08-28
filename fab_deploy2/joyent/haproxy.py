import os

from fab_deploy2.base import haproxy as base_haproxy
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, local, settings
from fabric.tasks import Task

class Haproxy(base_haproxy.Haproxy):
    """
    Install nginx
    """

    def _install_package(self):
        sudo("pkg_add haproxy")
        # Some package versions don't include user
        with settings(warn_only=True):
            sudo("groupadd haproxy")
            sudo("useradd -g haproxy -s /usr/bin/false haproxy")

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name='haproxy',
                host=[env.host_string])

    @task_method
    def stop(self):
        run('svcadm disable haproxy')

Haproxy().as_tasks()
