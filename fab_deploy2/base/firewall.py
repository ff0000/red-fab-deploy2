from fab_deploy2.config import CustomConfig

class TCPOptions(object):
    open_ports = CustomConfig.OPEN_PORTS
    internal_restricted_ports = CustomConfig.RESTRICTED_PORTS
    external_restricted_ports = CustomConfig.EX_RESTRICTED_PORTS

    allowed = CustomConfig.ALLOWED_SECTIONS
    ex_allowed = CustomConfig.EX_ALLOWED_SECTIONS
    proto = 'tcp'
    group = 200


    def __init__(self, conf):
        self.conf = conf
        self.server_sections = set(self.conf.server_sections())

    def get_line(self, port, interface=None, from_ip='any', section=None):
        return {
            'interface' : interface,
            'proto' : self.proto,
            'from_ip' : from_ip,
            'port' : port,
            'group' : self.group,
            'section': section
        }

    def get_optional_list(self, section, ports_option,
                          allowed_option, ip_option, interface,
                          enumerate_ips=True):
        lines = []
        # If we have restricted ports
        restricted_ports = self.conf.get_list(section, ports_option)
        if restricted_ports:
            if enumerate_ips:
                ips = []
                for section in self.conf.get_list(section, allowed_option):
                    ips.extend(self.conf.get_list(section, ip_option))

                # Add a line for each port
                for ip in ips:
                    ip = ip.split('@')[-1]
                    for port in restricted_ports:
                        line = self.get_line(port, interface, ip, section=None)
                        lines.append(line)
            else:
                for s in self.conf.get_list(section, allowed_option):
                    if s in self.server_sections:
                        for port in restricted_ports:
                            line = self.get_line(port, interface=interface, from_ip=None, section=s)
                            lines.append(line)

        return lines

    def get_config_list(self, section, internal, external):
        txt = []
        for port in self.conf.get_list(section, self.open_ports):
            txt.append(self.get_line(port))

        txt.extend(self.get_optional_list(section,
                                self.internal_restricted_ports,
                                self.allowed,
                                self.conf.INTERNAL_IPS,
                                internal))

        txt.extend(self.get_optional_list(section,
                                self.external_restricted_ports,
                                self.ex_allowed,
                                self.conf.CONNECTIONS,
                                external))
        return txt

class UDPOptions(TCPOptions):
    proto = 'udp'
    group = '300'

    open_ports = CustomConfig.UDP_OPEN_PORTS
    internal_restricted_ports = CustomConfig.UDP_RESTRICTED_PORTS
    external_restricted_ports = CustomConfig.UDP_EX_RESTRICTED_PORTS

    allowed = CustomConfig.UDP_ALLOWED_SECTIONS
    ex_allowed = CustomConfig.UDP_EX_ALLOWED_SECTIONS
