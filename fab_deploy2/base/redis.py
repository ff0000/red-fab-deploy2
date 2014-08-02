import os

from fabric.api import run, sudo, env, local, execute
from fabric.tasks import Task

from fab_deploy2.tasks import MultiTask, task_method

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
            results = execute('utils.get_ip', None, hosts=[master])
            master_ip = results[master]
            config.append(('# slaveof', "slaveof "))
            config.append(('^slaveof', "slaveof {0} {1}".format(
                                                    master_ip, port)))

        self._setup_config(config)

    @task_method
    def start(self):
        raise NotImplementedError()

    @task_method
    def stop(self):
        raise NotImplementedError()

    @task_method
    def promote_slave(self):
        """
        Promote given slave to master.
        """
        config = list(self.config)
        config.append(('^slaveof', "slaveof no one"))
        self._setup_config(config)


    def _install_package(self):
        raise NotImplementedError()

    def _setup_config(self, config):
        for k, v in config:
            origin = "%s " % k
            sudo('sed -i "/%s/ c\%s" %s' %(origin, v, self.config_location))
