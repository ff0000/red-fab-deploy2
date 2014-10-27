import sys

from fabric.api import task, run, env, sudo
from fabric.context_managers import settings

from fab_deploy2 import functions

@task
def get_ip(interface, hosts=[]):
    """
    get IP address
    """
    print run(get_ip_command(interface))
    return run(get_ip_command(interface))

def get_ip_command(interface):
    """
    get IP address
    """
    if not interface:
        interface = functions.execute_on_host('utils.get_interface')
    return 'ifconfig %s | grep Bcast | cut -d ":" -f 2 | cut -d " " -f 1' % interface


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
def get_interface(internal=True):
    interfaces = run('ip route list | grep kernel | cut -d " " -f 3')
    for i in interfaces.split():
        if not i:
            continue

        ip = run('ifconfig %s | grep Bcast | cut -d ":" -f 2 | cut -d " " -f 1' % i)
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.16.'):
            if internal:
                return i
        else:
            if not internal:
                return i

    raise Exception("Couldn't find an matching interface")


@task
def install_package(package_name, update=False, remote=None):
    with settings(warn_only=True):
        installed = run('rpm -qa | grep {0}'.format(package_name))

    if installed.return_code != 0:
        if remote:
            sudo('rpm -U --replacepkgs {0}'.format(remote))

        sudo('yum -y install {0}'.format(package_name))
        return True
    return False
