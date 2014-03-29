from fab_deploy2.operating_systems.redhat.firewall import *


class FirewallSetup(FirewallSetup):
    default_context = {
        'template' : 'iptables/iptables-rackspace.conf',
        'conf_location' : '/etc/sysconfig/iptables'
    }

setup = FirewallSetup()
