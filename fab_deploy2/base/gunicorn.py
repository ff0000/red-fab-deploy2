import os

from fabric.api import run, sudo, env
from fabric.tasks import Task

from fab_deploy2 import functions
from fab_deploy2.tasks import ServiceContextTask, task_method

class Gunicorn(ServiceContextTask):
    """
    Install gunicorn.
    """

    context_name = 'gunicorn'

    user = 'www'
    group = 'www'

    log_dir = '/var/log/gunicorn'
    log_name = 'django.log'

    gunicorn_name = 'gunicorn'


    default_context = {
        'num_workers' : 10,
        'listen_address' : '0.0.0.0:8000',
        'user' : user,
        'group' : group,
        'log_dir' : log_dir,
        'log_name' : log_name,
        'gunicorn_name' : gunicorn_name,
        'daemonize' : True,
        'project_path' : '/project/',
        'conf_location' : '',
    }

    def _setup_service(self):
        raise NotImplementedError()

    def get_task_context(self):
        context = super(Gunicorn, self).get_task_context()
        context['log_file'] = os.path.join(self.log_dir, self.log_name)
        context['start_script'] = os.path.join(env.configs_path,
                            "gunicorn/start_{0}.sh".format(self.gunicorn_name))
        context['config_location'] = os.path.join(env.configs_path,
                            "gunicorn/{0}.py".format(self.gunicorn_name))
        wsgi_file = os.path.join(env.project_path, 'project', 'wsgi.py')
        if os.path.exists(wsgi_file):
            context['use_wsgi'] = True
        return context

    def get_template_context(self):
        context = super(Gunicorn, self).get_template_context()
        context['python'] = functions.execute_on_host('python.context')
        context['newrelic'] = functions.get_context_from_role('newrelic')
        return context

    def upload_templates(self):
        context = self.get_template_context()
        functions.render_template("gunicorn/gunicorn.pt", context[self.context_name]['config_location'], context=context)
        script = functions.render_template("gunicorn/start_gunicorn.sh", context[self.context_name]['start_script'], context=context)
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
        functions.execute_on_host('python.setup', packages=['gunicorn'])
        self.upload_templates()
        path = self._setup_logs()
        self._setup_rotate(path)
        self._setup_service()

    @task_method
    def update(self):
        self.upload_templates()
        self._setup_service()
