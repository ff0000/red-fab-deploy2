import os

from fabric.api import run, sudo, env, settings
from fabric.tasks import Task
from fabric.operations import put
from fabric.contrib.files import append, exists

from fab_deploy2 import functions
from fab_deploy2.tasks import MultiContextTask, task_method

class Backups(MultiContextTask):
    context_name = 'backups'
    namespace = 'backups'

    tempcron = '/tmp/tmpcron'

    default_context = {
        'directory' : '',
        'backup_key' : '',
        'crontime' : '0 1 * * *',
        'delete' : True,
        'method' : 'size',
        'bucket' : '',
        'template' : 'backups/red-backups'
    }

    def add_packages(self):
        raise NotImplementedError()

    def grant_permission(self):
        raise NotImplementedError()

    def created_key(self, key_data):
        raise NotImplementedError()

    def _setup_ssh_key(self):
        home = run('pwd')
        ssh_dir = os.path.join(home, '.ssh')
        run('mkdir -p %s' % ssh_dir)
        rsa = os.path.join(ssh_dir, 'id_rsa')

        if not self.backup_key:
            if not exists(rsa, use_sudo=True):
                create = raw_input("An backup ssh key isn't specified in your environment. Should we create one on the server. (y/n):")
                if create and create.lower() == 'y':
                    run("ssh-keygen -t rsa -f %s -N ''" % rsa)
                    self.created_key(os.path.join(ssh_dir, 'id_rsa.pub'))
                else:
                    raise Exception("You chose not to create a new key. Please setup the backup key in your environment")
            else:
                print 'Using server key, assuming it already has been granted privileges'
        else:
            put(self.backup_key, rsa)

    def upload_templates(self):
        context = self.get_template_context()
        script = functions.render_template(self.template, context=context)
        run('chmod +x {}'.format(script))
        return script

    def add_to_cron(self, script, directory=None):
        directory = directory and directory or self.directory
        if not directory:
            raise Exception("You need to specifiy the directoy to backup. Either in your this command or in your environment.")

        options = ''
        if self.delete:
            options += '--delete '

        if self.bucket:
            options += '--bucket {0} '.format(self.bucket)

        python = run('which python')
        line = "{0} {1} {2} {3}backup {4}".format(self.crontime, python,
                                                script, options, directory)
        with settings(warn_only=True):
            run('crontab -l > {0}'.format(self.tempcron))

        append(self.tempcron, line)
        run('crontab {0}'.format(self.tempcron))


    @task_method
    def setup(self, directory=None, method=None, init=True):
        self.add_packages()
        self.grant_permission()
        script = self.upload_templates()
        self.add_to_cron(script, directory=directory)
        if init and str(init).lower() != 'false':
            bucket = ''
            if self.bucket:
                bucket += '--bucket {0} '.format(self.bucket)
            method = method and method or self.method

            line = "python {0} --compare-method {1} {2}init /tmp/".format(script, method, bucket)
            run(line)
