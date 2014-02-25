import os

from fabric.api import sudo, env
from fabric.contrib.files import append

from fab_deploy2.base import nginx as base_nginx
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions


class Nginx(base_nginx.Nginx):
    """
    Installs nginx
    """
    user = 'nginx'
    group = 'nginx'
    remote_config_path = '/etc/nginx/nginx.conf'

    def _install_package(self):
        sudo("rpm -U --replacepkgs http://nginx.org/packages/rhel/6/noarch/RPMS/nginx-release-rhel-6-0.el6.ngx.noarch.rpm")
        sudo("yum -y install nginx")

    def _setup_logging(self):
        path = os.path.dirname(os.path.realpath(self.access_log))
        sudo('mkdir -p %s' % path)
        sudo('chown -R %s:%s %s' % (self.user, self.group, path))
        sudo('chmod 666 %s' % path)
        self._setup_rotate(path)
        return path

    def _setup_rotate(self, path):
        text = [
        "%s/*.log {" % path,
        "   daily",
        "   missingok",
        "   rotate 52",
        "   compress",
        "   delaycompress",
        "   notifempty",
        "   create 640 nginx adm",
        "   sharedscripts",
        "   postrotate",
        "        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`",
        "   endscript",
        "}"]
        sudo('touch /etc/logrotate.d/nginx')
        append('/etc/logrotate.d/nginx', text, use_sudo=True)

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_service', name='nginx',
                host=[env.host_string])
    @task_method
    def stop(self):
        sudo('service nginx stop')

Nginx().as_tasks()
