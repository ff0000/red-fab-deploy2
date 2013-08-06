import os

from fab_deploy2.base import celery as base_celery
from fab_deploy2.tasks import task_method

from fabric.api import sudo, env
from fabric.contrib.files import append
from fabric.tasks import Task

class Celeryd(base_celery.Celeryd):

    user = 'www-data'
    group = 'www-data'
    conf_file = '/etc/supervisor/supervisord.conf'

    @task_method
    def start(self):
        sudo('supervisorctl start %s' % self.get_name())

    @task_method
    def stop(self):
        sudo('supervisorctl stop %s' % self.get_name())

    def _setup_service(self, env_value=None):
        # we use supervisor to control gunicorn
        sudo('apt-get -y install supervisor')
        celery_conf = os.path.join(env.remote_configs,
                                     'celery/%s.conf' % self.celery_name )
        celeryb_conf = os.path.join(env.remote_configs,
                                     'celery/%s.conf' % self.celerybeat_name )
        text = 'files = %s, %s' % (celery_conf, celeryb_conf)
        append(self.conf_file, text, use_sudo=True)
        sudo('supervisorctl update')

Celeryd().as_tasks()
