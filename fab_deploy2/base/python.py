import os

from fabric.api import env, sudo, run, local
from fabric.contrib import files
from fabric.operations import put

from fab_deploy2.tasks import MultiContextTask, task_method

class Python(MultiContextTask):
    context_name = 'python'
    name = 'setup'

    default_context = {
        'location' : '/srv/env',
        'name' : 'env',
        'files' : ['base.txt', 'production.txt']
    }

    def get_task_context(self):
        context = super(Python, self).get_task_context()
        if not context['location'].endswith('/'):
            context['location'] = context['location'] +'/'
        return context

    def get_update_file(self):
        return os.path.join(self.location, 'LAST_UPDATE')

    def update_hash(self, save=False):
        reqs = os.path.join(env.deploy_path, 'requirements')
        local('git log --pretty=format:"%h" -n 1 -- {} > tmp-r'.format(reqs))
        hash_code = open('tmp-r').read()
        local('rm tmp-r')
        if save:
            run('echo "{0}" > {1}'.format(hash_code, self.get_update_file()))
        return hash_code

    def should_update(self):
        match_file = self.get_update_file()
        if files.exists(match_file):
            last = run('cat {}'.format(match_file))
            if last == self.update_hash():
                return False
        return True

    def update_files(self):
        for f in self.files:
            put(os.path.join(env.deploy_path, 'requirements', f), self.location)
            run("{0} install --upgrade -r {1}".format(
                        os.path.join(self.location, 'bin', 'pip'),
                        os.path.join(self.location, f)))
            self.update_hash(save=True)

    @task_method
    def setup(self, use_files=True, packages=None):

        if not files.exists(self.location):
            sudo('mkdir -p {0}'.format(self.location))
            sudo('chown {0} {1}'.format(env.user, self.location))

            sudo('pip install virtualenv==1.10.1')
            run('virtualenv --system-site-packages {0}'.format(
                        os.path.join(self.location)))

        if use_files:
            if self.should_update():
                self.update_files()

        if packages:
            for package in packages:
                run("{0} install {1}".format(
                        os.path.join(self.location, 'bin', 'pip'),
                        package))

    @task_method
    def update(self):
        if self.should_update():
            self.update_files()
