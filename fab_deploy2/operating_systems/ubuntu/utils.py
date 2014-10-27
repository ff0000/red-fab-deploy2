import sys

from fabric.api import task, run, env, sudo
from fabric.context_managers import settings

@task
def get_ip(interface, hosts=[]):
    """
    get IP address
    """
    return run(get_ip_command(interface))

def get_ip_command(interface):
    """
    get IP address
    """
    if not interface:
        interface = 'eth0'
    return 'ifconfig %s | grep Bcast | cut -d ":" -f 2 | cut -d " " -f 1' % interface

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

@task
def install_package(package_name, update=False, remote=None):
    with settings(warn_only=True):
        installed = run('dpkg -s {0}'.format(package_name))

    if installed.return_code != 0:
        if remote:
            sudo('apt-get install -y python-software-properties')
            sudo('add-apt-repository {0}'.format(remote))

        if remote or update:
            sudo('apt-get update')

        sudo('apt-get install -y {0}'.format(package_name))
        return True
    return False
