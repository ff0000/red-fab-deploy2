import os

from fab_deploy2.base import gunicorn as base_gunicorn
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import sudo, env, settings
from fabric.contrib.files import append


class Gunicorn(base_gunicorn.Gunicorn):
    """
    Install gunicorn and set it up with supervisor.
    """

    user = 'nginx'
    group = 'nginx'
    daemonize = False
    upstart_name = 'upstart_gunicorn'

    @task_method
    def start(self):
        name = self.upstart_name
        with settings(warn_only=True):
            result = sudo('initctl status {0}'.format(name))
            if result.return_code == 0:
                sudo('initctl restart {0}'.format(name))
            else:
                sudo('initctl start {0}'.format(name))

    @task_method
    def stop(self):
        sudo('initctl stop {0}' % self.upstart_name)

    def _setup_service(self, env_value=None):
        gunicorn_conf = os.path.join(env.configs_path,
            "gunicorn/{0}.conf".format(
                self.upstart_name))
        # Copy instead of linking so upstart
        # picks up the changes
        sudo('cp %s /etc/init/' % gunicorn_conf)
        sudo('initctl reload-configuration')

    def upload_templates(self):
        context = super(Gunicorn, self).upload_templates()
        functions.render_template("gunicorn/upstart_gunicorn.conf",
                        os.path.join(
                            env.configs_path, "gunicorn/{0}.conf".format(
                                self.upstart_name)),
                        context=context)

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
