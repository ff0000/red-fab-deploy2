import os
import tempfile

from fab_deploy2.base import backups as base_backups
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, settings
from fabric.tasks import Task
from fabric.contrib.files import get

from smartdc import DataCenter

new_context = base_backups.Backups.default_context.copy()
new_context['manta_url'] = 'https://us-east.manta.joyent.com'


class Backups(base_backups.Backups):
    """
    Setup backups to manta for this server.
    """

    default_context = new_context

    def get_template_context(self):
        key_id = run("ssh-keygen -l -f ~/.ssh/id_rsa.pub | awk '{print $2}' | tr -d '\n'")
        if not key_id:
            raise Exception("Couldn't get key id")

        context = super(Backups, self).get_template_context()
        context['account'] = env.joyent_account
        context['key_id'] = key_id

        context['mail'] = env.get('mail', {})
        context['mail']['subject'] = '{0} {1} backups'.format(env.host_string, self.bucket)
        return context

    def add_packages(self):
        # Makes no sense, but their package doesn't install the bin
        with settings(warn_only=True):
            functions.execute_on_host('utils.install_package',
                                        package_name='sdc-manta')
            functions.execute_on_host('utils.install_package',
                                        package_name='py27-gdbm')
            result = run('which mls')
            if not result.succeeded:
                functions.execute_on_host('utils.install_package',
                                        package_name='scmgit')
                sudo('npm install manta -g')

    def grant_permission(self):
        self._setup_ssh_key()

    def created_key(self, pub_key_path):
        key_name = raw_input('Enter your ssh key name: ')
        key_id = '/%s/keys/%s' % ( env.joyent_account, key_name)
        allow_agent = env.get('allow_agent', False)
        sdc = DataCenter(key_id=key_id, allow_agent=allow_agent)

        with tempfile.TemporaryFile() as f:
            get(pub_key_path, f)
            f.seek(0)
            data = f.read()

        sdc.add_key(env.host_string, data)


Backups().as_tasks()
