from fabric.api import local, env, execute
from fabric.tasks import Task

from fab_deploy2.functions import get_answer, get_remote_name

class InternalIps(Task):
    """
    Updates your server.ini config with the correct
    internal ip addresses for all hosts

    This is a serial task, that should not be called
    with any remote hosts as the remote hosts to run
    on is determined by the hosts in your server.ini
    file.
    """

    name = 'update_internal_ips'
    serial = True

    def run(self):
        conf = env.config_object
        for section in conf.server_sections():
            internals = conf.get_list(section, conf.INTERNAL_IPS)
            connections = conf.get_list(section, conf.CONNECTIONS)
            if len(internals) != len(connections):
                raise Exception("Number of connections and internal ips do not match")

            if internals:
                results = execute('utils.get_ip', None, hosts=connections)
                for i, conn in enumerate(connections):
                    internals[i] = results[conn]

                conf.set_list(section, conf.INTERNAL_IPS, internals)
                conf.save(env.conf_filename)

update_internal_ips = InternalIps()
