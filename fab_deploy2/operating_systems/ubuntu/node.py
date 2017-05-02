import os

from fabric.api import env, sudo, run, local
from fabric.contrib import files
from fabric.operations import put

from fab_deploy2 import functions
from fab_deploy2.tasks import MultiContextTask, task_method

class Node(MultiContextTask):
    context_name = 'node'
    name = 'setup'

    static_folder = '/srv/active/collected-static/'
    app_file = 'server.js'


    @task_method
    def setup(self, use_files=True, packages=None):
        self._install_package()


    @task_method
    def update(self):
        pass


    def _install_package(self):
        sudo('curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -')
        installed = functions.execute_on_host('utils.install_package', package_name='nodejs')
        if installed:
            sudo('npm update -g npm')
            sudo('npm install -g pm2')
            sudo('npm install -g express')
            sudo('npm install -g morgan')
            sudo('npm install -g http-proxy-middleware')

    @task_method
    def start(self):
        self.stop()
        app_filepath = os.path.join(self.static_folder, self.app_file)
        sudo('pm2 start %s' % app_filepath)

    @task_method
    def stop(self):
        app = os.path.splitext(self.app_file)[0]
        sudo('pm2 stop %s' % app)


    @task_method
    def restart(self):
        app = os.path.splitext(self.app_file)[0]
        sudo('pm2 restart %s' % app)

Node().as_tasks()
