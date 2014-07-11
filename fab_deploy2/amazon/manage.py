from fabric.api import  env
from fabric.tasks import Task

from utils import get_security_group
from api import get_ec2_connection

from fab_deploy2.base.firewall import TCPOptions

from fab_deploy2.config import CustomConfig

from boto.exception import EC2ResponseError

class AmazonTCPOptions(TCPOptions):

    def get_config_list(self, section):
        txt = []
        for port in self.conf.get_list(section, self.open_ports):
            txt.append(self.get_line(port, from_ip='0.0.0.0/0'))

        txt.extend(self.get_optional_list(section,
                                self.internal_restricted_ports,
                                self.allowed,
                                self.conf.INTERNAL_IPS,
                                None, False))

        txt.extend(self.get_optional_list(section,
                                self.external_restricted_ports,
                                self.ex_allowed,
                                self.conf.CONNECTIONS,
                                None))
        return txt

class AmazonUDPOptions(AmazonTCPOptions):
    proto = 'udp'
    group = '300'

    open_ports = CustomConfig.UDP_OPEN_PORTS
    internal_restricted_ports = CustomConfig.UDP_RESTRICTED_PORTS
    external_restricted_ports = CustomConfig.UDP_EX_RESTRICTED_PORTS

    allowed = CustomConfig.UDP_ALLOWED_SECTIONS
    ex_allowed = CustomConfig.UDP_EX_ALLOWED_SECTIONS

class FirewallSync(Task):
    """
    Update security group policies of AWS based on info read from server.ini

    Under each section defining a type of server, you will find 'open-ports',
    'restricted_ports' and 'allowed-sections' variables.  This task will open
    'open-ports' for the corresponding type of server, and restricted access of
    'restricted_ports' to only servers defined in 'allowed-sections'.

    No effort is made to remove any rules that are not present in
    server.ini
    """

    name = 'firewall_sync'
    serial = True
    _groups = {}

    def _get_lb_sg(self):
        elb_conn = get_ec2_connection(server_type='elb')
        elb = elb_conn.get_all_load_balancers()
        if elb:
            conn = get_ec2_connection(server_type='ec2')
            sg = elb[0].source_security_group
            groups = conn.get_all_security_groups(groupnames=[sg.name])
            self._groups['load-balancer'] = groups[0]
            return self._groups['load-balancer']
        return None

    def get_security_group(self, section):
        if not section in self._groups:
            if section == 'load-balancer':
                self._groups[section] = self._get_lb_sg()
            else:
                conn = get_ec2_connection(server_type='ec2')
                self._groups[section] = get_security_group(conn, section)
        return self._groups[section]

    def run(self, section=None):
        conf = env.config_object

        if section:
            sections = [section]
        else:
            sections = conf.server_sections()

        udp_options = AmazonUDPOptions(env.config_object)
        tcp_options = AmazonTCPOptions(env.config_object)

        for section in sections:
            # don't process load balancer directly
            if section == 'load-balancer':
                continue

            udp_list = udp_options.get_config_list(section)
            tcp_list = tcp_options.get_config_list(section)

            host_sg = self.get_security_group(section)
            if host_sg:
                for line in (udp_list + tcp_list):
                    try:
                        if line.get('from_ip'):
                            cidr = line['from_ip']
                            if not '/' in cidr:
                                cidr = '{0}/32'.format(cidr)
                            host_sg.authorize(line['proto'], line['port'], line['port'], cidr)
                        else:
                            sg = self.get_security_group(line.get('section'))
                            if sg:
                                host_sg.authorize(line['proto'], line['port'], line['port'],
                                                      src_group=sg)

                    except EC2ResponseError, e:
                        if not e.error_code or e.error_code != "InvalidPermission.Duplicate":
                            raise
firewall_sync = FirewallSync()
