from fabric.api import  env
from fabric.tasks import Task

from utils import get_security_group
from api import get_ec2_connection


class FirewallSync(Task):
    """
    Update security group policies of AWS based on info read from server.ini

    Under each section defining a type of server, you will find 'open-ports',
    'restricted_ports' and 'allowed-sections' variables.  This task will open
    'open-ports' for the corresponding type of server, and restricted access of
    'restricted_ports' to only servers defined in 'allowed-sections'.

    Because we use non VPC load balancer of AWS, our load balancer has no
    related EC2 instance. Therefore, security policies related to load-balancer
    are different from other types of servers.
    1.  It inherits security policy of elastic load balancer from amazon-elg-sg
        group for itself, so we don't need to define it by ourselves.
    2.  It is not associted with specific instance, so if load-balancer is in
        allowed-sections, we just allow access from the whole amazon-elb/amazon-elb-sg
        group.
    """

    name = 'firewall_sync'
    serial = True

    def _get_lb_sg(self, **kwargs):
        elb_conn = get_ec2_connection(server_type='elb', **kwargs)
        elb = elb_conn.get_all_load_balancers()
        if elb:
            return elb[0].source_security_group
        return None

    def run(self, section=None, **kwargs):
        conf = env.config_object
        conn = get_ec2_connection(server_type='ec2', **kwargs)

        if section:
            sections = [section]
        else:
            sections = conf.server_sections()

        for section in sections:

            open_ports = conf.get_list(section, conf.OPEN_PORTS)
            restricted_ports = conf.get_list(section, conf.RESTRICTED_PORTS)

            if (not open_ports and not restricted_ports
                or section == 'load-balancer'):
                continue

            host_sg = get_security_group(conn, section)
            if open_ports:
                for port in open_ports:
                    try:
                        host_sg.authorize('tcp', port, port, '0.0.0.0/0')
                    except:
                        pass

            if restricted_ports:
                for s in conf.get_list(section, conf.ALLOWED_SECTIONS):
                    if s == 'load-balancer':
                        guest_sg = self._get_lb_sg(**kwargs)
                    else:
                        guest_sg = get_security_group(conn, s)

                    if guest_sg:
                        for port in restricted_ports:
                            try:
                                if s == 'load-balancer':
                                    conn.authorize_security_group(host_sg.name,
                                          src_security_group_name='amazon-elb-sg',
                                          src_security_group_owner_id='amazon-elb',
                                          from_port=port, to_port=port,
                                          ip_protocol='tcp')
                                else:
                                    host_sg.authorize('tcp', port, port,
                                                      src_group=guest_sg)
                            except:
                                pass

firewall_sync = FirewallSync()
