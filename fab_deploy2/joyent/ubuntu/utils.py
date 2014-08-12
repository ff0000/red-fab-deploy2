import sys

from fabric.api import task, run, env, sudo

from fab_deploy2.operating_systems.ubuntu.utils import *

@task
def get_ip(interface, hosts=[]):
    """
    get IP address
    """
    if not interface:
        interfaces = run('ip route list | grep kernel | cut -d " " -f 3')
        for i in interfaces.split():
            if not i:
                continue

            ip = run('ifconfig %s | grep Bcast | cut -d ":" -f 2 | cut -d " " -f 1' % i)
            if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.16.'):
                return ip

    return run(get_ip_command(interface))
