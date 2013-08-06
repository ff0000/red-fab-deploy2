import sys

from fabric.api import task, run, env, sudo
from fabric.context_managers import settings

@task
def start_or_restart_supervisor(name, hosts=[]):
    """
    """
    sudo('supervisorctl update')
    with settings(warn_only=True):
        result = sudo('supervisorctl status {0}'.format(name))
        if 'RUNNING' in result:
            sudo('supervisorctl restart {0}'.format(name))
        else:
            sudo('supervisorctl start {0}'.format(name))

@task
def start_or_restart_service(name, hosts=[]):
    """
    """
    with settings(warn_only=True):
        result = sudo('service {0} status'.format(name))
        if result.return_code == 0:
            sudo('service {0} restart'.format(name))
        else:
            sudo('service {0} start'.format(name))
