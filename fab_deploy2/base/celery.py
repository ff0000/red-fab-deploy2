import os

from fabric.api import run, sudo, env
from fabric.tasks import Task

from fab_deploy2 import functions
from fab_deploy2.tasks import ServiceContextTask, task_method

class Celeryd(ServiceContextTask):
    """
    Install celery.
    """

    context_name = 'celeryd'

    log_dir = '/var/log/celery'
    log_name = 'celeryd.log'

    name = 'celeryd'

    default_context = {
        'num_workers' : 2,
        'user' : 'www',
        'group' : 'www',
        'log_dir' : log_dir,
        'log_name' : log_name,
        'nodes' : 'celery',
        'pid_dir' : '/var/www',
        'name' : name,
        'timelimit' : '300',
        'conf_location' : ''
    }

    def _setup_service(self):
        raise NotImplementedError()

    def get_task_context(self):
        context = super(Celeryd, self).get_task_context()
        context['start_script'] = os.path.join(env.configs_path,
                            "celery/start_{0}.sh".format(self.name))
        return context

    def get_template_context(self):
        context = super(Celeryd, self).get_template_context()
        context['python'] = functions.execute_on_host('python.context')
        context['newrelic'] = functions.get_context_from_role('newrelic')
        return context

    def upload_templates(self):
        context = self.get_template_context()
        script = functions.render_template("celery/start_celeryd.sh", context[self.context_name]['start_script'], context=context)
        sudo('chmod +x {}'.format(script))
        return context

    def _setup_logs(self):
        path = os.path.join(self.log_dir, self.log_name)
        sudo('mkdir -p %s' % self.log_dir)
        sudo('touch %s' % path)
        sudo('chown -R %s:%s %s' % (self.user, self.group, self.log_dir))
        sudo('chmod 666 %s' % path)
        return path

    def _setup_rotate(self, path):
        raise NotImplementedError()

    @task_method
    def setup(self):
        sudo("mkdir -p {0}".format(self.pid_dir))
        sudo('chown -R %s:%s %s' % (self.user, self.group, self.pid_dir))

        functions.execute_on_host('python.setup', packages=['django-celery'])
        self.upload_templates()
        path = self._setup_logs()
        self._setup_rotate(path)
        self._setup_service()

    @task_method
    def update(self):
        self.upload_templates()
        self._setup_service()
