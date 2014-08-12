import os

from fab_deploy2.base import celery as base_celery
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env
from fabric.tasks import Task

class Celeryd(base_celery.Celeryd):
    """
    Install celery and set it up with svcadm.
    """

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name=self.name)

    @task_method
    def stop(self):
        run('svcadm disable %s' % self.name)

    def get_service_path(self):
        return os.path.join(env.configs_path,
                            "celery/{0}.xml".format(self.name))

    def upload_templates(self):
        context = super(Celeryd, self).upload_templates()
        functions.render_template("celery/celeryd.xml",
                        self.get_service_path(),
                        context=context)
        return context

    def _setup_service(self):
        path = self.get_service_path()
        run('svccfg import %s' % path)

    def _setup_rotate(self, path):
        sudo('logadm -C 3 -p1d -c -w %s -z 1' % path)

Celeryd().as_tasks()
