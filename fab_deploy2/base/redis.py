import os

from fabric.api import run, sudo, env, local
from fabric.tasks import Task

from fab_deploy2.tasks import MultiTask, task_method
from fab_deploy2 import functions

class RedisInstall(MultiTask):
    """
    Install redis
    """

    name = 'setup'

    config = (
        ('^bind', '#bind 127.0.0.1'),
    )
    config_location = None

    @task_method
    def setup(self, master=None, port=6379, hosts=[]):
        self._install_package()
        config = list(self.config)
        if master:
            results = functions.execute_on_platform('utils.get_ip', None, hosts=[master])
            master_ip = results[master]
            config.append(('# slaveof', "slaveof "))
            config.append(('^slaveof', "slaveof {0} {1}".format(
                                                    master_ip, port)))

        self._setup_config(config)
        functions.execute_if_exists('collectd.install_plugin', 'redis')

    @task_method
    def start(self):
        raise NotImplementedError()

    @task_method
    def stop(self):
        raise NotImplementedError()

    def _install_package(self):
        raise NotImplementedError()

    def _setup_config(self, config):
        for k, v in config:
            origin = "%s " % k
            sudo('sed -i "/%s/ c\%s" %s' %(origin, v, self.config_location))
