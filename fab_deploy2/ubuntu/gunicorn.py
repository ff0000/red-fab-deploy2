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

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart_supervisor', name=self.gunicorn_name)

    @task_method
    def stop(self):
        sudo('supervisorctl stop %s' % self.gunicorn_name)

    def _setup_service(self, env_value=None):
        sudo('apt-get -y install supervisor')
        conf_file = '/etc/supervisor/supervisord.conf'
        gunicorn_conf = os.path.join(env.configs_path, "gunicorn/supervisor_{0}.conf".format(self.gunicorn_name))
        text = 'files = %s' % gunicorn_conf
        append(conf_file, text, use_sudo=True)
        sudo('supervisorctl update')

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
