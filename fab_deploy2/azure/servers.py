import sys
import importlib
from fabric.api import env
from fabric.tasks import Task

from fab_deploy2 import functions
from fab_deploy2.base import servers as base_servers
from fab_deploy2.tasks import task_method




class APIServer(base_servers.BaseServer):
    name = 'api_server'
    config_section = 'api-server'

    packages = []

    def _install_packages(self):
        for package in self.packages:
            functions.execute_on_host('utils.install_package', package_name=package)

    def _setup_services(self):
        functions.execute_on_host('gunicorn.setup')

    def _restart_services(self):
        functions.execute_on_host('gunicorn.start')

    def _update_server(self, branch=None, update_configs=True, link_code=True):
        if not branch:
            branch = self.git_branch

        if env.get('deploy_ready') != branch:
            functions.execute_on_host('local.deploy.prep_code',
                    branch=branch)
            env.deploy_ready = branch

        functions.execute_on_host('local.deploy.deploy_code',
                branch=branch)

        if link_code:
            self._link_code()

        if update_configs:
            self._update_configs()
        functions.execute_on_host('python.update')

    def _update_configs(self):
        functions.execute_on_host('gunicorn.update')

    def get_context(self):
        defaults = {
            'gunicorn' : { 'listen_address' : '0.0.0.0:8000' },
        }

        context = super(APIServer, self).get_context()
        return functions.merge_context(context, defaults)




class AzureIsoServer(base_servers.LBServer):
    name = 'iso_server'
    config_section = 'iso-server'

    packages = []
    
    def _install_packages(self):
        for package in self.packages:
            functions.execute_on_host('utils.install_package', package_name=package)

    def _setup_services(self):
        super(AzureIsoServer, self)._setup_services()
        functions.execute_on_host('node.setup')

    def _restart_services(self):
        super(AzureIsoServer, self)._restart_services()
        functions.execute_on_host('node.start')

    def _update_server(self, *args, **kwargs):
        super(AzureIsoServer, self)._update_server(*args, **kwargs)
        functions.execute_on_host('node.update')

    def _update_configs(self):
        super(AzureIsoServer, self)._update_configs()
        functions.execute_on_host('node.update')

    def get_context(self):
        lbs = env.config_object.get_list('load-balancer',
                                          env.config_object.INTERNAL_IPS)
        defaults = {
            'nginx' : { 'lbs' : lbs },
            'node' : { 'listen_address' : '0.0.0.0:8001' },
        }

        context = super(AzureIsoServer, self).get_context()
        return functions.merge_context(context, defaults)