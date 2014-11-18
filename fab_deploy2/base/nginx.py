import os

from fabric.api import run, sudo, env, local
from fabric.tasks import Task

from fab_deploy2.tasks import ServiceContextTask, task_method
from fab_deploy2 import functions

class Nginx(ServiceContextTask):
    """
    Install nginx
    """

    name = 'setup'
    remote_config_path = '/opt/local/etc/nginx/nginx.conf'
    context_name = "nginx"

    default_context = {
        'user' : 'www',
        'group' : 'www',
        'worker_processes' : 4,
        'worker_rlimit' : 65000,
        'worker_connections' : 2048,
        'keepalive_timeout' : 65,
        'hash_max_size' : 2048,
        'client_max_body_size' : '1m',
        'mime_template' : 'nginx/mime.types',
        'access_log' : '/var/log/nginx/access.log',
        'error_log' : '/var/log/nginx/error.log',
        'do_cache' : False,
        'cache_key' : '$scheme$request_uri',
        'cache_time' : '2m',
        'cache_location' :' /var/www/cache',
        'cache_tmp_location' : '/var/www/cache-tmp',
        'cache_inactive' : '60m',
        'cache_size' : '512m',
        'upstream_max_fails' : 5,
        'upstream_timeout' : '60s',
        'listen' : 80,
        'static_location' : '/srv/collected-static',
        'static_expiry' : '1y',
        'uploads_location' : '/srv/uploads',
        'uploads_expiry' : '1M',
        'auth_file' : '',
        'lbs' : [],
        'upstream_addresses' : ['127.0.0.1'],
        'upstream_port' : '8000',
        'template' : 'nginx/nginx.conf',
        'hosts': [],
        'status': True,
        'forward_header' : 'X-Cluster-Client-Ip'
    }

    @task_method
    def setup(self, template=None, directory=None):
        self._install_package()
        self._setup_logging()
        self._setup_dirs()
        self._setup_config(template=template, directory=directory)
        functions.execute_if_exists('collectd.install_plugin', 'nginx')

    @task_method
    def update(self, template=None, directory=None):
        self._setup_config(template=template, directory=directory)

    def _install_package(self):
        raise NotImplementedError()

    def _setup_logging(self):
        raise NotImplementedError()

    def _setup_dirs(self):
        for d in (self.cache_location, self.cache_tmp_location,
                  self.uploads_location):
            sudo('mkdir -p %s' % d)
            sudo('chown -R %s:%s %s' % (self.user, self.group, d))
        # This we deploy two should be owned by normal user
        sudo('mkdir -p %s' % self.static_location)
        sudo('chown {0} {1}'.format(env.user, self.static_location))

    def _setup_config(self, template=None, directory=None):
        if not template:
            template = self.template

        name = template.split('/')[-1]
        if directory:
            remote_config_path = os.path.join(directory, name)
        else:
            remote_config_path = self.remote_config_path

        context = self.get_template_context()
        mime_path = functions.render_template(self.mime_template, context=context)
        context['nginx']['mime_types_file'] = mime_path
        nginx_config = functions.render_template(template, context=context)
        sudo('ln -sf %s %s' % (nginx_config, remote_config_path))
