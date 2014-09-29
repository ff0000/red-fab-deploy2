import os

from fab_deploy2.base import redis as base_redis
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env
from fabric.tasks import Task


class Redis(base_redis.RedisInstall):
    """
    Install redis
    """
    config_location = '/etc/redis.conf'

    def _install_package(self):
        sudo('yum -y install epel-release')
        sudo('yum -y install redis')
        sudo('chkconfig redis on')

    @task_method
    def start(self):
        functions.execute_on_host(
            'utils.start_or_restart_service', name='redis')

    @task_method
    def stop(self):
        sudo('service redis stop')

Redis().as_tasks()
