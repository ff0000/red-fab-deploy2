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
    config_location = '/opt/local/etc/redis.conf'

    def _install_package(self):
        functions.execute_on_host('utils.install_package',
                        package_name='redis')

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name='redis')

    @task_method
    def stop(self):
        run('svcadm disable redis')

Redis().as_tasks()
