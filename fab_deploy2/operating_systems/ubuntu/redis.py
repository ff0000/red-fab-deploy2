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
    config_location = '/etc/redis/redis.conf'

    def _install_package(self):
        installed = functions.execute_on_host('utils.install_package', package_name='redis-server')
        if installed:
            sudo('update-rc.d redis-server defaults')

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_service', name='redis-server')

    @task_method
    def stop(self):
        sudo('service redis-server stop')

Redis().as_tasks()
