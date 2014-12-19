import os

from fab_deploy2 import functions

from fabric.api import local, env, execute, run, get
from fabric.tasks import Task
from fabric.utils import abort
from fabric.context_managers import settings, hide
from fabric.contrib.files import exists

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

    def _sync_files(self, code_dir):
        """
        Sync all files, copy from last version if possible.

        code_dir: the location of this code. Includes a git hash.
        """

        run('mkdir -p {0}'.format(code_dir))
        local('rsync -rptov --checksum --progress --delete-after {0}/ {1}:{2}updating'.format(
            env.build_dir, env.host_string, env.base_remote_path))

        run('mkdir -p {0}'.format(code_dir))
        run('cp -r {0}updating/* {1}/'.format(env.base_remote_path, code_dir))

    def build_settings(self, code_dir):
        functions.execute_on_host('local.deploy.build_settings', code_dir=code_dir)

    def _post_sync(self, code_dir, code_hash):
        """
        Hook that is executed after a sync.

        """
        self.build_settings(code_dir)        

    def run(self, branch=None):
        """
        """
        if not branch:
            branch = 'master'

        code_hash = open(os.path.join(env.build_dir, CODE_VERSION)).read()
        code_dir = os.path.join(env.base_remote_path, 'code', code_hash)

        self._sync_files(code_dir)
        self._post_sync(code_dir, code_hash)

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
        local('cp -r {0}/collected-static {1}/'.format(env.project_path,
                                                    env.build_dir))

    def _restore_working_dir(self):
        with settings(warn_only=True):
            with hide('running', 'warnings'):
                # Fail if there was no stash by this name
                result = local('git stash list stash@{0} | grep %s' % self.stash_name )

            if not result.failed:
                local('git stash pop')

    def _record_spots(self, branch):
        local('git log --pretty=format:"%h" -n 1 {0} -- {1} > {2}'.format(
            branch,
            os.path.join(env.project_path, env.track_static),
            os.path.join(env.build_dir, STATIC_VERSION)
        ))
        local('git log --pretty=format:"%h" -n 1 {0} > {1}'.format(
            branch,
            os.path.join(env.build_dir, CODE_VERSION)
        ))


    def run(self, branch=None):
        if not branch:
            branch = 'master'

        self._clean_working_dir(branch)
        execute('local.git.build', branch=branch, hosts=['none'])
        self._prep_static()

        self._record_spots(branch)
        self._restore_working_dir()


class LinkCode(Task):

    name = 'update_code_links'
    cache_prefix = 'c-'
    max_keep = 5
    code_static_dir = 'collected-static'

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
        if exists(static_dir):
            run('find -L {0} -maxdepth 1 -type l -exec rm "{{}}" \;'.format(static_dir))


    def _link_static(self, code_dir, static_dir):
        location = os.path.join(code_dir, STATIC_VERSION)
        static_hash = run('tail {0}'.format(location))
        assert static_hash

        code_static_dir = os.path.join(code_dir, self.code_static_dir)

        run('rsync -rptov --checksum  --delete-after --filter "P {0}*" "{1}/" "{2}"'.format(self.cache_prefix, code_static_dir, static_dir))
        run('ln -sfn {0} {1}/c-{2}'.format(code_static_dir, static_dir, static_hash))

    def _link_active(self, code_dir):
        active_dir = os.path.join(env.base_remote_path, 'active')
        run('ln -sfn {0} {1}'.format(code_dir, active_dir))

    def run(self, code_hash=None):
        """
        Link active to a code directory

        Default implementation links deployed code to the active locations
        and updates static and purges old code.
        """

        if not code_hash:
            code_hash = run('tail {0}'.format(
                    os.path.join(env.base_remote_path, 'updating', CODE_VERSION)))

        if not code_hash:
            raise Exception("Code hash not found, do a full deploy")

        code_dir = os.path.join(env.base_remote_path, 'code', code_hash)
        if not exists(code_dir):
           raise Exception("{0} does not exist, do a full deploy".format(code_dir))

        static_dir = functions.execute_on_host('nginx.context')['static_location']

        self._link_static(code_dir, static_dir)
        self._link_active(code_dir)
        self._purge(static_dir)

class MigrateDB(Task):
    name = 'migrate_db'

    def migrate(self, code_hash):
        manager = os.path.join(env.base_remote_path, 'code', code_hash, 'project', 'manage.py')
        if exists(manager):
            context = functions.execute_on_host('python.context')
            run('{0}bin/python {1} migrate'.format(context['location'], manager))
        else:
           raise Exception("{0} does not exist, do a full deploy".format(code_dir))

    def run(self, code_hash=None):
        """
        Run a migration command.
        """

        if not code_hash:
            code_hash = run('tail {0}'.format(
                    os.path.join(env.base_remote_path, 'updating', CODE_VERSION)))

        if not code_hash:
            raise Exception("Code hash not found, do a full deploy")

        self.migrate(code_hash)

class BuildSettings(Task):
    """ Builds your settings file.

    Attributes
    ----------
    name : str
        An invocation name for this task.

    """

    name = 'build_settings'


    def _get_context(self, role):
        """ Return a template context for settings generation.

        Returns
        -------
        out : dict
            Template context dictionary.

        """
        context = functions.get_role_context(role).get('django', {})
        context.update({
            'nginx' : functions.execute_on_host('nginx.context')
        })
        return context

    def _build_settings(self, code_dir):
        """ Construct a new settings file.

        Notes
        -----
        To ensure an idempotent outcome, the rendered settings template
        is appended to a "pristine" copy of the settings/__init__.py file
        (grabbed here from /srv/updating/project/settings/__init__.py).
        The existing __init__.py file is then clobbered.

        Parameters
        ----------
        code_dir : str
            Path to the code directory.

        """
        template_name = 'django/base_settings'
        role = env.host_roles.get(env.host_string)
        if os.path.exists(os.path.join(env.deploy_path, 'templates',
                        'django', role)):
            template_name = "django/{0}".format(role)

        pristine_location = os.path.join(env.base_remote_path, 'updating',
                'project', 'settings', '__init__.py')

        template_location = functions.render_template(template_name, context=self._get_context(role))
        run('cat {0} {1} > {2}'.format(pristine_location, template_location,
                        os.path.join(code_dir, 'project',
                                    'settings', '__init__.py')
                        )
        )

    def _read_remote_file(self, path):
        """ Return the contents of a remote file.

        Parameters
        ----------
        path : string
            The path to a remote file to read.

        Raises
        ------
        IOError
            If the requested path cannot be found.

        Returns
        -------
        out : string
            The contents of the remote file.

        """

        if exists(path):
            from StringIO import StringIO
            fd = StringIO()
            get(path, fd)
            return fd.getvalue()
        else:
            raise IOError('Remote file not found at path "{0}"'.format(path))


    def run(self, code_dir=None):
        """ Handle task execution.

        Parameters
        ----------
        code_dir : str, optional
            The code directory for the relevant deployment.
            Will be determined automatically if omitted.

        """
        if code_dir is None:
            remote_version_path = os.path.join(env.base_remote_path,
                    'updating', CODE_VERSION)
            try:
                code_hash = self._read_remote_file(remote_version_path)
                code_dir = os.path.join(env.base_remote_path, 'code', code_hash)
            except IOError as e:
                abort('Please make sure to build and deploy first!  (Encountered: {0})'.format(e))

        self._build_settings(code_dir)


build_settings = BuildSettings()
deploy_code = DeployCode()
prep_code = PrepDeploy()
update_code_links = LinkCode()
migrate_db = MigrateDB()
