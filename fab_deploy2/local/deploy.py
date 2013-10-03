import os

from fab_deploy2 import functions

from fabric.api import local, env, execute, run
from fabric.tasks import Task
from fabric.context_managers import settings, hide

STATIC_VERSION = 'VERSION'
CODE_VERSION = 'CVERSION'

class DeployCode(Task):
    """
    Deploys your project.

    Takes one optional argument:
        branch: The branch that you would like to push.
                If it is not provided 'master' will be used.


    This rsync's your built files to the online server
    and sim links the newly uploaded location to
    the active location.
    """

    name = 'deploy_code'
    cache_prefix = 'c-'
    max_keep = 5

    def _purge(self, static_dir):
        """
        Delete old code directories and purge broken static links
        """

        purge = """
        while [ "$(ls {0} | wc -l)" -gt {1} ]; do
            list=$(find "{0}" -maxdepth 1 -mindepth 1 -type d -printf '%T@ %p:\n' \
                2>/dev/null | sort -n)
            line=$(echo $list | cut -s -d ":" -f 1)
            dir="${{line#* }}"
            rm -rf $dir
        done
        """.format(os.path.join(env.base_remote_path, 'code'),
                   self.max_keep)
        run(purge)
        run('find -L {0} -maxdepth 1 -type l -exec rm "{{}}" \;'.format(static_dir))

    def _sync_files(self, code_dir, static_dir, active_dir):
        """
        Sync all files, copy from last version if possible.
        """

        run('mkdir -p {0}'.format(code_dir))
        static_hash = open(os.path.join(env.build_dir, STATIC_VERSION)).read()
        assert static_hash

        code_static_dir = os.path.join(code_dir, 'collected-static')

        local('rsync -rptov --checksum --progress --delete-after {0}/ {1}:/srv/updating'.format(env.build_dir, env.host_string, code_dir))

        run('mkdir -p {0}'.format(code_dir))
        run('cp -r /srv/updating/* {0}/'.format(code_dir))
        run('rsync -rptov --delete-after --filter "P {0}*" "{1}/" "{2}"'.format(self.cache_prefix, code_static_dir, static_dir))
        run('ln -sfn {0} {1}/c-{2}'.format(code_static_dir, static_dir, static_hash))

    def _post_sync(self, code_dir, static_dir, active_dir):
        """
        Hook that is executed after a sync.

        Purges old deployments and links in active
        """
        self._purge(static_dir)
        run('ln -sfn {0} {1}'.format(code_dir, active_dir))


    def run(self, branch=None):
        """
        """
        if not branch:
            branch = 'master'

        local('git log --pretty=format:"%h" -n 1 {0} > tmp'.format(branch))
        code_hash = open('tmp').read()
        local('rm tmp')
        active_dir = os.path.join(env.base_remote_path, 'active')
        code_dir = os.path.join(env.base_remote_path, 'code', code_hash)
        static_dir = functions.execute_on_host('nginx.context')['static_location']

        self._sync_files(code_dir, static_dir, active_dir)
        self._post_sync(code_dir, static_dir, active_dir)

class PrepDeploy(Task):
    """
    Preps your static files for deployment.

    Takes one optional argument:
        branch: The branch that you would like to push.
                If it is not provided 'master' will be used.


    Internally this stashes any changes you have, checks out the
    requested branch, runs scripts/build.sh and then the
    django command collected static.

    If anything was stashed in the beginning it trys to restore it.

    This is a serial task, that should not be called directly
    with any remote hosts as it performs no remote actions.
    """

    serial = True
    stash_name = 'deploy_stash'
    name = 'prep_code'

    def _clean_working_dir(self, branch):
        """
        """
        # Force a checkout
        local('git stash save %s' % self.stash_name)
        local('git checkout %s' % branch)

    def _prep_static(self):
        build_script = os.path.join(env.project_path, 'scripts', 'build.sh')
        if os.path.exists(build_script):
            local('sh %s' % build_script)
        local('{0}/env/bin/python {0}/project/manage.py collectstatic --clear --noinput'.format(env.project_path))

        # restore the local gitkeep file in collected-static
        local('touch {0}'.format(os.path.join(
            env.project_path, 'collected-static', '.gitkeep')))

    def _restore_working_dir(self):
        with settings(warn_only=True):
            with hide('running', 'warnings'):
                # Fail if there was no stash by this name
                result = local('git stash list stash@{0} | grep %s' % self.stash_name )

            if not result.failed:
                local('git stash pop')

    def build_settings(self):
        template_name = 'django/base_settings'
        role = env.host_roles.get(env.host_string)
        if os.path.exists(os.path.join(env.deploy_path, 'templates',
                        'django', role)):
            template_name = "django/{0}".format(role)

        context = functions.get_role_context(role).get('django', {})

        # Update media root
        context.update({
            'nginx' : functions.execute_on_host('nginx.context')
        })

        template = functions.template_to_string(template_name, context)
        with open(os.path.join(env.build_dir, 'project',
                               'settings', '__init__.py'),
                  "a") as f:
            f.write(template)

    def _record_spots(self, branch):
        local('git log --pretty=format:"%h" -n 1 {0} -- {1} > {2}'.format(
            branch,
            os.path.join(env.project_path, env.track_static),
            os.path.join(env.build_dir, STATIC_VERSION)
        ))

    def run(self, branch=None):
        if not branch:
            branch = 'master'

        self._clean_working_dir(branch)
        execute('local.git.build', branch=branch, hosts=['none'])
        self.build_settings()
        self._prep_static()
        local('cp -r {0}/collected-static {1}/'.format(env.project_path,
                                                    env.build_dir))

        self._record_spots(branch)
        self._restore_working_dir()

deploy_code = DeployCode()
prep_code = PrepDeploy()
