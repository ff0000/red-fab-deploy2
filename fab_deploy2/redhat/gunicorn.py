import os

from fab_deploy2.base import gunicorn as base_gunicorn
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import sudo, env
from fabric.contrib.files import append


class Gunicorn(base_gunicorn.Gunicorn):
    """
    Install gunicorn and set it up with supervisor.
    """

    user = 'nginx'
    group = 'nginx'
    daemonize = False

    @task_method
    def start(self):
        with settings(warn_only=True):
            result = sudo('start %s' % self.get_name())

        if result.failed:
            self.restart()

    @task_method
    def stop(self):
        sudo('stop %s' % self.get_name())

    def _setup_service(self, env_value=None):
        gunicorn_conf = os.path.join(env.configs_path,
            "gunicorn/supervisor_{0}.conf".format(
                self.gunicorn_name))
        # Copy instead of linking so upstart
        # picks up the changes
        sudo('cp %s /etc/init/' % gunicorn_conf)
        sudo('initctl reload-configuration')

    def upload_templates(self):
        context = super(Gunicorn, self).upload_templates()

        return context

    def _setup_rotate(self, path):
        text = [
        "%s {" % path,
        "    copytruncate",
        "    size 1M",
        "    rotate 5",
        "}"]
        sudo('touch /etc/logrotate.d/%s.conf' % self.gunicorn_name)
        append('/etc/logrotate.d/%s.conf' % self.gunicorn_name,
                                    text, use_sudo=True)

Gunicorn().as_tasks()
