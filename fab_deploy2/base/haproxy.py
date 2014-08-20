import os

from fabric.api import run, sudo, env, local
from fabric.tasks import Task

from fab_deploy2.tasks import ServiceContextTask, task_method
from fab_deploy2 import functions

class Haproxy(ServiceContextTask):
    """
    Install nginx
    """

    name = 'setup'
    context_name = "haproxy"

    default_context = {
        'user' : 'haproxy',
        'group' : 'haproxy',
        'maxconn' : 40000,
        'contimeout' : 30000,
        'clitimeout' : 50000,
        'srvtimeout' : 50000,
        'mode' : 'http',
        'httpchk_url' : '/',
        'httpchk_retries' : '3',
        'port' : '80',
        'stats_port' : '9000',
        'stats_user' : 'stats',
        'stats_pw' : 'stats',
        'upstream_addresses' : [],
        'upstream_port' : '80',
        'upstream_check' : True,
        'upstream_slowstart' : 10000,
        'upstream_timeout' : '60s',
        'balance' : 'leastconn',
        'cookie' : '',
        'cookie_mode' : 'insert',
        'cookie_prefix' : 'a-',
        'template' : 'haproxy/haproxy.cfg',
        'remote_config_path' : '/opt/local/etc/haproxy.cfg',
        'loghost' : '127.0.0.1',
        'loglevel' : 'notice',
        'logfile' : '/var/log/haproxy.log',
        'loglocal' : 'local1',
        'stats_socket' : '/var/run/haproxy-stats.sock',
        'stats_timeout' : '1m',
        'rsyslog_conf' : '/opt/local/etc/rsyslog.conf',

    }

    @task_method
    def setup(self, template=None):
        self._install_package()
        self._setup_config(template=template)
        functions.execute_if_exists('collectd.install_plugin', 'haproxy')

    @task_method
    def update(self, template=None):
        self._setup_config(template=template)

    def _install_package(self):
        raise NotImplementedError()

    def _setup_logging(self):
        raise NotImplementedError()

    def _setup_config(self, template=None,):
        if not template:
            template = self.template

        context = self.get_template_context()
        self._setup_logging()
        config = functions.render_template(template, context=context)
        sudo('ln -sf %s %s' % (config, self.remote_config_path))
