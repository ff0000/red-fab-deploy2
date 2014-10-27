from fab_deploy2.base import nginx as base_nginx
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions
from fabric.api import sudo, env

class Nginx(base_nginx.Nginx):
    """
    Installs nginx
    """
    user = 'www-data'
    group = 'www-data'
    remote_config_path = '/etc/nginx/nginx.conf'

    def _install_package(self):
        installed = functions.execute_on_host('utils.install_package', package_name='nginx')
        if installed:
            sudo('update-rc.d nginx defaults')

    def _setup_logging(self):
        # Done by package
        pass

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_service', name='nginx',
                host=[env.host_string])
    @task_method
    def stop(self):
        sudo('service nginx stop')

Nginx().as_tasks()
