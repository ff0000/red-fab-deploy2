from fabric.api import task, run

def get_ip(interface, hosts=[]):
    """
    get IP address
    """
    # for amazon we don't ips since they may change
    # NOTE: on VPC's, public-hostname returns 404, so
    # we will use local-ipv4 instead
    if not interface:
        resp = run(
            'curl -s -o /dev/null -w "%{http_code}" http://169.254.169.254/latest/meta-data/public-hostname')
        if resp == '404':
            return run(
                'curl -s http://169.254.169.254/latest/meta-data/local-ipv4')
        else:
            return run(
                'curl -s http://169.254.169.254/latest/meta-data/public-hostname')

    return run(get_ip_command(interface))


def get_ip_command(interface):
    """
    get IP address
    """
    if not interface:
        interface = 'eth0'
    return 'ifconfig %s | grep Bcast | cut -d ":" -f 2 | cut -d " " -f 1' % interface


def get_security_group(conn, section):
    """
    Get security group
    If not exists, create one, enable ssh access and return it

    The security groups are named after the section name in server.ini.
    For example, if section is 'app-server', the security group will be
    called 'app-server-sg'.
    """

    sg_name = '%s-sg' % section
    try:
        groups = conn.get_all_security_groups(groupnames=[sg_name])
        return groups[0]
    except:
        grp = conn.create_security_group(sg_name,
                                             'security group for %s' % section)
        grp.authorize('tcp', 22, 22, '0.0.0.0/0')
        return grp
