from fabric.api import local, env, execute, run
from fabric.tasks import Task
from fabric.context_managers import cd


class GitBuild(Task):
    """
    Builds your code in a local directory
    based on the current branch
    """

    name = 'build'

    def run(self, branch=None, hosts=[]):
        if not branch:
           branch = 'master'

        local('mkdir -p {0}'.format(env.build_dir))
        local('touch {0}/tmp'.format(env.build_dir))
        local('rm -r {0}/*'.format(env.build_dir))
        local('git --git-dir="{0}/.git" "--work-tree={1}" checkout -f {2}'.format(env.project_path, env.build_dir, branch))

build = GitBuild()
