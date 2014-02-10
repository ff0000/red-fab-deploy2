import sys

from fabric.api import task, run, env, sudo
from fabric.context_managers import settings


@task
def get_ip(interface, hosts=[]):
    """
    get IP address
    TODO: This is a copy from amazon utils.py. But since amazon
    is tied to Ubuntu, we need to further decouple cloud platform
    and OS.
    """
    # for amazon we don't ips since they may change
    if not interface:
        return run(
            'curl -s http://169.254.169.254/latest/meta-data/local-ipv4')

    return run(get_ip_command(interface))


def get_ip_command(interface):
    """
    get IP address
    """
    if not interface:
        interface = 'eth0'
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
