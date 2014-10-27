from fab_deploy2.base import haproxy as base_haproxy
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, local, settings
from fabric.contrib.files import append

class Haproxy(base_haproxy.Haproxy):
    """
    Installs haproxy
    """
    user = 'www-data'
    group = 'www-data'
    remote_config_path = '/etc/haproxy/haproxy.cfg'
    rsyslog_conf = "/etc/defaults/rsyslog.conf"
    loghost = '/dev/log'
    loglocal = 'local0'

    def _install_package(self):
        installed = functions.execute_on_host('utils.install_package', package_name='haproxy')
        if installed:
            sudo('update-rc.d haproxy defaults')
        append("/etc/default/haproxy", "ENABLED=1", use_sudo=True)

    def _setup_logging(self):
        pass

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_service', name='haproxy',
                host=[env.host_string])
    @task_method
    def stop(self):
        sudo('service haproxy stop')

Haproxy().as_tasks()
