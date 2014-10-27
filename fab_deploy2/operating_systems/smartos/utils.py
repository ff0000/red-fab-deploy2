import random
from fabric.api import task, run, sudo
from fabric.context_managers import settings

from fab_deploy2 import functions

INTERNAL_RANGES = [
    '10.0.0.0/8',
    '192.168.0.0/16',
    '172.16.0.0/12'
]

@task
def get_ip(interface, hosts=[]):
    """
    """
    return run(get_ip_command(interface))

def get_ip_command(interface):
    """
    """
    if not interface:
        interface = functions.execute_on_host('utils.get_interface')

    return 'ifconfig %s | grep inet | grep -v inet6 | cut -d ":" -f 2 | cut -d " " -f 2' % interface

@task
def get_interface(iprange=None):
    ranges = tuple(INTERNAL_RANGES)
    if iprange:
        ranges = [iprange]
    for ip in ranges:
        interface = run("netstat -rn -f dst:{0} | tail -n 1 | tr -s ' ' ' ' | cut -d ' ' -f 6".format(ip))
        if interface:
            return interface

    raise Exception("Couldn't find an matching interface")

@task
def start_or_restart(name, hosts=[]):
    """
    """
    with settings(warn_only=True):
        run('svcadm refresh {0}'.format(name))
        result = run('svcs {0}'.format(name))
        if 'maintenance' in result:
            run('svcadm clear {0}'.format(name))
            run('svcadm enable {0}'.format(name))
        elif 'disabled' in result:
            run('svcadm enable {0}'.format(name))
        else:
            run('svcadm restart {0}'.format(name))


@task
def install_package(package_name, update=False, remote=None):
    with settings(warn_only=True):
        installed = run('pkg_info -E {0}'.format(package_name))

    if installed.return_code != 0:
        sudo('pkg_add {0}'.format(package_name))
        return True
    return False
