import random
from fabric.api import task, run
from fabric.context_managers import settings

@task
def get_ip(interface, hosts=[]):
    """
    """
    return run(get_ip_command(interface))

def get_ip_command(interface):
    """
    """
    if not interface:
        interface = 'net1'
    return 'ifconfig %s | grep inet | grep -v inet6 | cut -d ":" -f 2 | cut -d " " -f 2' % interface

@task
def start_or_restart(name, hosts=[]):
    """
    """
    with settings(warn_only=True):
        run('svcadm refresh {0}'.format(name))
        result = run('svcs {0}'.format(name))
        if 'maintenance' in result:
            run('svcadm clear {0}'.format(name))
        elif 'disabled' in result:
            run('svcadm enable {0}'.format(name))
        else:
            run('svcadm restart {0}'.format(name))
