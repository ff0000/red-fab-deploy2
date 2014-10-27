import os

from fab_deploy2.base import celery as base_celery
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import sudo, env
from fabric.contrib.files import append
from fabric.tasks import Task

class Celeryd(base_celery.Celeryd):
    """
    Install celery and set it up with supervisor.
    """

    user = 'www-data'
    group = 'www-data'
    conf_file = '/etc/supervisor/supervisord.conf'
    conf_location = '/etc/supervisor/conf.d/'

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_supervisor', name=self.name)

    @task_method
    def stop(self):
        sudo('supervisorctl stop %s' % self.name)

    def upload_templates(self):
        context = super(Celeryd, self).upload_templates()
        functions.render_template("celery/supervisor_celeryd.conf",
                        os.path.join(env.configs_path, "celery/supervisor_{0}.conf".format(self.name)),
                        context=context)
        return context

    def _setup_service(self, env_value=None):
        # we use supervisor to control gunicorn
        installed = functions.execute_on_host('utils.install_package', package_name='supervisor')
        if installed:
            sudo('update-rc.d supervisor defaults')

        if self.conf_location:
            celery_conf = os.path.join(env.configs_path,
                                    "celery/supervisor_{0}.conf".format(self.name))
            sudo('ln -sf {0} {1}'.format(celery_conf, self.conf_location))

    def _setup_rotate(self, path):
        text = [
        "%s {" % path,
        "    copytruncate",
        "    size 1M",
        "    rotate 5",
        "}"]
        sudo('touch /etc/logrotate.d/%s.conf' % self.name)
        for t in text:
            append('/etc/logrotate.d/%s.conf' % self.name,
                                        t, use_sudo=True)

Celeryd().as_tasks()
