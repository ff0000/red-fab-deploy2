import ConfigParser

class CustomConfig(ConfigParser.ConfigParser):
    """
    Custom Config class that can read and write lists.
    """

    # Config settings
    CONNECTIONS = 'connections'
    INTERNAL_IPS = 'internal-ips'

    #TCP
    OPEN_PORTS = 'open-ports'
    EX_RESTRICTED_PORTS = 'ex-restricted-ports'
    EX_ALLOWED_SECTIONS = 'ex-allowed-sections'
    RESTRICTED_PORTS = 'restricted-ports'
    ALLOWED_SECTIONS = 'allowed-sections'

    # UDP
    UDP_OPEN_PORTS = 'udp-open-ports'
    UDP_EX_RESTRICTED_PORTS = 'udp-ex-restricted-ports'
    UDP_EX_ALLOWED_SECTIONS = 'udp-ex-allowed-sections'
    UDP_RESTRICTED_PORTS = 'udp-restricted-ports'
    UDP_ALLOWED_SECTIONS = 'udp-allowed-sections'

    # Postgres
    USERNAME = 'username'
    REPLICATOR = 'replicator'
    REPLICATOR_PASS = 'replicator-password'

    # GIT
    GIT_SYNC = 'git-sync'

    # Amazon
    EC2_KEY_NAME = 'ec2-key-name'
    EC2_KEY_FILE = 'ec2-key-file'

    def get_list(self, section, key):
        """
        """
        if not self.has_option(section, key):
            return []

        return [x.strip() for x in self.get(section, key).split(',') if x.strip() ]

    def set_list(self, section, key, slist):
        """
        """
        t = ','.join(slist)
        self.set(section, key, t)

    def save(self, filename):
        """
        """
        fp = open(filename, 'w')
        self.write(fp)
        fp.close()

    def server_sections(self, include_other=False):
        sections = self.sections()
        return [ x for x in sections \
                if not self.has_option(x, 'is_server') or
                    self.getboolean(x, 'is_server') ]
