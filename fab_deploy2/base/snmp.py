import os

from fab_deploy2 import functions
from fab_deploy2.config import CustomConfig
from fab_deploy2.tasks import ContextTask

from fabric.api import run, sudo, env, put, local
from fabric.tasks import Task


class SNMPSetup(ContextTask):
    """
    Sync a snmp config file
    """

    name = 'setup'
    remote_config_path = '/opt/local/etc/snmpd.conf'
    context_name = 'snmp'
    config_section = 'monitor'

    template = 'snmp/snmp.conf'
    default_context = {
        'template' : template
    }

    def _add_package(self):
        raise NotImplementedError()

    def _restart_service(self):
        raise NotImplementedError()

    def get_task_context(self):
        context = super(SNMPSetup, self).get_task_context()
        context['community'] = env.config_object.get(self.config_section, 'community')
        context['ips'] = env.config_object.get_list(self.config_section,env.config_object.CONNECTIONS)
        context['ips'].extend(
                env.config_object.get_list(self.config_section,
                        env.config_object.INTERNAL_IPS))
        return context

    def run(self):
        self._add_package()
        context = self.get_template_context()
        template = context[self.context_name].get('template', self.template)
        dest_path = functions.render_template(template, self.template,
                                              context=context)
        sudo("ln -sf {0} {1}".format(dest_path, self.remote_config_path))
        self._restart_service()
