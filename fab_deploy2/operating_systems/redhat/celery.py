import os

from fab_deploy2.base import celery as base_celery
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import sudo, env, settings
from fabric.contrib.files import append
from fabric.tasks import Task

class Celeryd(base_celery.Celeryd):
    user = 'nginx'
    group = 'nginx'
    upstart_name = 'upstart_celeryd'

    def get_task_context(self):
        context = super(Celeryd, self).get_task_context()
        context['config_file'] = os.path.join(
            env.configs_path, "celery/{0}.conf".format(self.upstart_name))
        return context

    def upload_templates(self):
        context = super(Celeryd, self).upload_templates()
        conf = functions.render_template("celery/{0}.conf".format(self.upstart_name),
                                         context[self.context_name]['config_file'],
                                         context=context)
        return context

    def _setup_service(self):
        celeryd_conf = os.path.join(
            env.configs_path, "celery/{0}.conf".format(self.upstart_name))
        # Copy instead of linking so upstart
        # picks up the changes
        sudo('cp %s /etc/init/' % celeryd_conf)
        sudo('initctl reload-configuration')

    def _setup_rotate(self, path):
        text = [
        "%s {" % path,
        "    copytruncate",
        "    size 1M",
        "    rotate 5",
        "}"]
        sudo('touch /etc/logrotate.d/%s.conf' % self.name)
        for t in text:
            append('/etc/logrotate.d/%s.conf' % self.name, t, use_sudo=True)

    @task_method
    def start(self):
        name = self.upstart_name
        with settings(warn_only=True):
            # initctl status does not return logical
            # exit code so just restart or start instead
            result = sudo('initctl restart {0}'.format(name))
            if result.return_code != 0:
                sudo('initctl start {0}'.format(name))

    @task_method
    def stop(self):
        sudo('initctl stop %s' % self.upstart_name)

Celeryd().as_tasks()
