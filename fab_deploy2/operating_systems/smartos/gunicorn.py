import os

from fab_deploy2.base import gunicorn as base_gunicorn
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env
from fabric.tasks import Task

class Gunicorn(base_gunicorn.Gunicorn):
    """
    Install gunicorn and set it up with svcadm.
    """

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name=self.gunicorn_name)

    @task_method
    def stop(self):
        run('svcadm disable %s' % self.gunicorn_name)

    def get_service_path(self):
        return os.path.join(env.configs_path,
                            "gunicorn/{0}.xml".format(self.gunicorn_name))

    def upload_templates(self):
        context = super(Gunicorn, self).upload_templates()
        functions.render_template("gunicorn/gunicorn.xml",
                        self.get_service_path(),
                        context=context)
        return context

    def _setup_service(self):
        path = self.get_service_path()
        run('svccfg import %s' % path)

    def _setup_rotate(self, path):
        sudo('logadm -C 3 -p1d -c -w %s -z 1' % path)


Gunicorn().as_tasks()
