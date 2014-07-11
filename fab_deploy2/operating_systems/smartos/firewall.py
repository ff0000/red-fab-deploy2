import os

from fab_deploy2 import functions
from fab_deploy2.tasks import ContextTask
from fab_deploy2 import functions
from fab_deploy2.base.firewall import TCPOptions, UDPOptions
from fabric.api import run, sudo, env, put, local
from fabric.tasks import Task


class FirewallSetup(ContextTask):
    """
    Setup ipfilter as a firewall
    """

    context_name = 'ipf'
    default_context = {}
    name = "setup"

    def get_task_context(self):
        context = super(FirewallSetup, self).get_task_context()
        role = env.host_roles.get(env.host_string)
        if not role:
            raise Exception("Unknown role for %s" % env.host_string)

        context['internal_interface'] = functions.execute_on_host('utils.get_interface')
        context['external_interface'] = functions.execute_on_host('utils.get_interface', iprange='0.0.0.0')
        context['tcp_lines'] = TCPOptions(env.config_object).get_config_list(role,
                                    context['internal_interface'],
                                    context['external_interface'])
        context['udp_lines'] = UDPOptions(env.config_object).get_config_list(role,
                                    context['internal_interface'],
                                    context['external_interface'])
        return context

    def run(self):
        context = self.get_template_context()
        file_loc = functions.render_template("ipf/ipf.conf", context=context)
        run('svccfg -s ipfilter:default setprop firewall_config_default/policy = astring: "custom"')
        run('svccfg -s ipfilter:default setprop firewall_config_default/custom_policy_file = astring: "{0}"'.format(file_loc))
        functions.execute_on_host('utils.start_or_restart', name='ipfilter')

setup = FirewallSetup()
