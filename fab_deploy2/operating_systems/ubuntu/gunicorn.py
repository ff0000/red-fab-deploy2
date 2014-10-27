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

    user = 'www-data'
    group = 'www-data'
    daemonize = False
    conf_location = '/etc/supervisor/conf.d/'

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_supervisor', name=self.gunicorn_name)

    @task_method
    def stop(self):
        sudo('supervisorctl stop %s' % self.gunicorn_name)

    def _setup_service(self, env_value=None):
        installed = functions.execute_on_host('utils.install_package', package_name='supervisor')
        if installed:
            sudo('update-rc.d supervisor defaults')
        if self.conf_location:
            gunicorn_conf = os.path.join(env.configs_path,
                        "gunicorn/supervisor_{0}.conf".format(self.gunicorn_name))
            sudo('ln -sf {0} {1}'.format(gunicorn_conf, self.conf_location))

    def upload_templates(self):
        context = super(Gunicorn, self).upload_templates()
        functions.render_template("gunicorn/supervisor_gunicorn.conf",
                        os.path.join(env.configs_path, "gunicorn/supervisor_{0}.conf".format(self.gunicorn_name)),
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
        for t in text:
            append('/etc/logrotate.d/%s.conf' % self.gunicorn_name,
                                        t, use_sudo=True)

Gunicorn().as_tasks()
