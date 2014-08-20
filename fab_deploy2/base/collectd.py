import os
import re

from fab_deploy2 import functions
from fab_deploy2.config import CustomConfig
from fab_deploy2.tasks import ServiceContextTask, task_method

from fabric.api import run, sudo, env, put, local
from fabric.contrib.files import append, exists

from jinja2.exceptions import TemplateNotFound

class Collectd(ServiceContextTask):
    """
    Sync a collectd config
    """

    name = 'setup'
    context_name = 'collectd'
    namespace = 'collectd'

    default_context = {
        'template' : 'collectd/collectd.conf',
        'base_dir' : '/var/lib/collectd',
        'remote_config_path' : '/etc/collectd/collectd.conf',
        'plugin_configs' : '/etc/collectd/collectd.d/',
        'plugin_path' : '/usr/lib/collectd/',
        'types_db' : '/usr/share/collectd/types.db',
        'config_section' : 'collectd-receiver',
        'interval' : 20,
        'base_plugins' : ('cpu', 'load', 'interface', 'logfile', 'df',
                          'disk','processes','swap', 'tcpconns', 'memory',
                          'network', 'threshold'),
        'package_name' : 'collectd',
        'package_names' : None,
        'timeout' : 2,
        'threads' : 5,
        'collectd_tar' : 'collectd-5.4.0'
    }

    def _add_package(self, name):
        raise NotImplementedError()

    def _plugin_context(self, plugin):
        data = {}
        context_func = '{0}_context'.format(plugin)
        if hasattr(self, context_func):
            data.update(getattr(self, context_func)())
        data.update(self._get_plugin_env_context(plugin))
        return data

    def _get_plugin_env_context(self, plugin):
        key = 'collectd_{0}'.format(plugin)
        data = env.context.get(key, {})
        role = env.host_roles.get(env.host_string)
        if role:
            role_dict = functions.get_role_context(role)
            data.update(role_dict.get(key, {}))
        return data

    def _install_plugin(self, plugin, context, **kwargs):
        task_name = 'collectd.{0}_setup'.format(plugin)
        task = functions.get_task_instance(task_name)
        package_names = self.package_names
        if task:
            functions.execute_on_host(task_name, **kwargs)
        else:
            if package_names and plugin in package_names:
                self._add_package(package_names[plugin])

            self.render_plugin_configs(plugin, context, **kwargs)

    def render_plugin_configs(self, plugin, context, **overides):
        if not env.task_context.get(env.host_string + 'pdir'):
            sudo('mkdir -p {0}'.format(self.plugin_configs))
            env.task_context[env.host_string + 'pdir'] = True

        plugin_context = self._plugin_context(plugin)
        plugin_context.update(overides)
        local_context = dict(context)
        local_context[plugin] = plugin_context

        plugin_path = None
        threshold_path = None
        try:
            template = plugin_context.get("template",
                            "collectd/{0}.conf".format(plugin))
            plugin_path = functions.render_template(template,
                                     context=local_context)
        except TemplateNotFound:
            pass

        try:
            template = plugin_context.get("threshold_template",
                                    "collectd/threshold-{0}.conf").format(plugin)
            threshold_path = functions.render_template(template,
                                     context=local_context)
        except TemplateNotFound:
            pass

        if plugin_path:
            sudo('ln -sf {0} {1}'.format(plugin_path, self.plugin_configs))

        if threshold_path:
            path = os.path.join(self.plugin_configs, 'thresholds.conf')
            sudo("echo '\n<Plugin \"threshold\">' > {0} && find {1}collectd/ -name threshold-* -exec cat {{}} \; >> {0} && echo '\n</Plugin>\n' >> {0}".format(path, env.configs_path))

    @task_method
    def setup(self, *args, **kwargs):
        self._add_package(self.package_name)
        context = self.get_template_context()

        template = context[self.context_name].get('template', self.template)
        for plugin in self.base_plugins:
            self._install_plugin(plugin, context)

        context['connection'] = re.sub(r'[^a-zA-Z0-9-]', '-', env.host_string)
        context['role'] = env.host_roles.get(env.host_string)
        dest_path = functions.render_template(template, self.template,
                                              context=context)
        sudo("ln -sf {0} {1}".format(dest_path, self.remote_config_path))

    @task_method
    def install_plugin(self, plugin, **kwargs):
        """
        Installs a plugin only if there is a collectd section in your config
        """
        if not env.config_object.has_section(self.config_section):
            print "Cowardly refusing to install plugin because there is no {0} section in your servers.ini".format(self.config_section)
        elif not exists(self.plugin_path):
            print "Cowardly refusing to install plugin because {0} does not exist".format(self.plugin_path)
        else:
            self._install_plugin(plugin, self.get_template_context(), **kwargs)

    @task_method
    def install_rrd_receiver(self):
        context = self.get_template_context()
        self._install_plugin('rrdtool', context)

        context['network'] = self._plugin_context('network')
        auth_file = functions.render_template("collectd/auth.conf", context=context)
        self._install_plugin('network', context, auth_file=auth_file)

    def _get_collectd_headers(self):
        raise NotImplementedError()

    def _add_to_types(self, new_types):
        filename = self.types_db
        for t in new_types:
            append(filename, t, use_sudo=True)

    def _gcc_share_args(self):
        return ""

    @task_method
    def redis_setup(self):
        """
        The redis that comes with collectd uses credis.
        That doesn't work with newer redis versions.
        So we install hiredis and compile this version source
        and copy the plugin in.
        """
        path = self._get_collectd_headers()
        context = self._plugin_context('redis')
        functions.execute_on_host('hiredis.setup')

        run('wget --no-check-certificate {0}'.format(context['plugin_url']))
        run("gcc -DHAVE_CONFIG_H -I{0} -I{0}core -Wall -Werror -g -O2 -fPIC -DPIC -o redis.o -c redis.c".format(path))
        run('gcc -shared redis.o {0} -Wl,-lhiredis -Wl,-soname -Wl,redis.so -o redis.so'.format(self._gcc_share_args()))
        sudo('cp redis.so {0}'.format(self.plugin_path))

        self._add_to_types([
            'blocked_clients           value:GAUGE:0:U',
            'changes_since_last_save   value:GAUGE:0:U',
            'pubsub                    value:GAUGE:0:U',
            'expired_keys              value:GAUGE:0:U',
        ])
        run('rm redis.*')
        self.render_plugin_configs('redis', self.get_template_context())

    @task_method
    def haproxy_setup(self):
        """
        Compile the haproxy plugin and copy it in.
        """
        context = self._plugin_context('haproxy')
        path = self._get_collectd_headers()
        run('wget --no-check-certificate {0}'.format(context['plugin_url']))

        run('gcc -DHAVE_CONFIG_H -I{0} -I{0}core -Wall -Werror -g -O2 -c haproxy.c  -fPIC -DPIC -o haproxy.o'.format(path))
        run('gcc -shared haproxy.o {0} -Wl,-soname -Wl,haproxy.so -o haproxy.so'.format(self._gcc_share_args()))
        sudo('cp haproxy.so {0}'.format(self.plugin_path))
        self._add_to_types([
            'hap_sessions  total:ABSOLUTE:0:U, rate:ABSOLUTE:0:U',
            'hap_bytes  rx:COUNTER:0:1125899906842623, tx:COUNTER:0:1125899906842623',
            'hap_errors  req:COUNTER:0:1125899906842623, rsp:COUNTER:0:1125899906842623, con:COUNTER:0:1125899906842623',
            'hap_deny  req:COUNTER:0:1125899906842623, rsp:COUNTER:0:1125899906842623',
            'hap_status  value:GAUGE:0:100',
            'hap_http_codes 1xx_codes:DERIVE:0:1125899906842623, 2xx_codes:DERIVE:0:1125899906842623, 3xx_codes:DERIVE:0:1125899906842623, 4xx_codes:DERIVE:0:1125899906842623, 5xx_codes:DERIVE:0:1125899906842623 other:DERIVE:0:1125899906842623',
        ])
        run('rm haproxy.*')
        self.render_plugin_configs('haproxy', self.get_template_context())

    def postgresql_context(self):
        data = {
            'username' : env.config_object.get('db-server', 'replicator'),
            'password' : env.config_object.get('db-server', 'replicator-password')
        }
        data.update(self._get_plugin_env_context('postgresql'))
        if not 'name' in data:
            if env.config_object.has_option('db-server', 'db-name'):
                database_name = env.config_object.get('db-server', 'db-name')
            else:
                database_name = None
                while not database_name:
                    database_name = raw_input('Enter your database name: ')
                    env.config_object.set('db-server', database_name)
            data['name'] = database_name

        return data

    def network_context(self):
        if env.config_object.has_section(self.config_section):
            return {
                'target_host' : env.config_object.get_list(self.config_section,env.config_object.CONNECTIONS),
                'username' : env.config_object.get(self.config_section,"username"),
                'password' : env.config_object.get(self.config_section,"password")
            }
        else:
            return {}

    def rrdtool_context(self):
        return {
            'location' : os.path.join(self.base_dir, 'rrd'),
            'wps' : '100',
            'flush' : '120'
        }

    def haproxy_context(self):
        return {
            'plugin_url' : 'https://raw.githubusercontent.com/Fotolia/collectd-mod-haproxy/master/haproxy.c',
        }

    def redis_context(self):
        return {
            'plugin_url' : 'https://raw.githubusercontent.com/ajdiaz/collectd/hiredis/src/redis.c',
        }

    def nginx_context(self):
        return {
            'url' : 'http://localhost/nginx_status'
        }
