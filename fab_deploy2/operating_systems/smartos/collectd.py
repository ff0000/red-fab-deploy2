import os

from fab_deploy2.base import collectd as base_collectd
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, put, local
from fabric.contrib.files import exists, append, sed
from fabric.context_managers import cd
from fabric.operations import put

class Collectd(base_collectd.Collectd):
    """
    Setup collectd
    """

    plugin_path = '/opt/local/lib/collectd'
    base_dir = '/var/db/collectd'
    types_db = '/opt/local/share/collectd/types.db'
    plugin_configs = '/opt/local/etc/collectd.d/'
    remote_config_path = '/opt/local/etc/collectd.conf'
    name = 'setup'
    package_names = {
        'curl': 'collectd-curl',
        'network': 'collectd-network',
        'notify_email': 'collectd-notify-email',
        'postgresql': 'collectd-postgresql93',
        'rrdtool': 'collectd-rrdtool',
        'nginx': 'collectd-curl'
    }
    base_plugins = ('zonecpu', 'load', 'interface', 'logfile', 'df',
                          'zonevfs','swap', 'zonememory', 'network', 'threshold')
    collectd_tar = 'collectd-5.4.1'

    def _add_package(self, name):
        if name == self.package_name:
            functions.execute_on_host('utils.install_package', package_name='gcc47')
        functions.execute_on_host('utils.install_package', package_name=name)

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name='collectd')

    @task_method
    def stop(self):
        sudo('svcadm disable collectd')

    def _get_collectd_headers(self):
        """
        Thanks to a bug in collectd we have to configure and force
        htonll to be 1 so we can build
        """
        if not exists('{0}.tar.gz'.format(self.collectd_tar)):
            run('wget http://collectd.org/files/{0}.tar.gz'.format(self.collectd_tar))
            run('tar -xvf {0}.tar.gz'.format(self.collectd_tar))
            with cd(self.collectd_tar):
                sed('configure', '# Check for htonll', '$as_echo "#define HAVE_HTONLL 1" >>confdefs.h')
                run('./configure')

        return "{0}/src/".format(self.collectd_tar)


    def _zone_context(self, name):
        return {
            'plugin_file' : os.path.join(env.configs_dir, 'modules', 'smartos',
                                         self.collectd_tar, '{0}.c'.format(name)),
        }

    def _zone_setup(self, name):
        context = self._plugin_context(name)
        path = self._get_collectd_headers()
        plugin = context['plugin_file']
        put(plugin, '{0}.c'.format(name))
        run('gcc -DHAVE_CONFIG_H -I{0} -I{0}core -Wall -Werror -g -O2 -c {1}.c  -fPIC -DPIC -o {1}.o'.format(path, name))
        run('gcc -shared  {0}.o -Wl,-soname -Wl,{0}.so -o {0}.so'.format(name))
        sudo('cp {0}.so {1}'.format(name, self.plugin_path))

    @task_method
    def zonememory_setup(self):
        self._zone_setup('zonememory')

    @task_method
    def zonecpu_setup(self):
        self._zone_setup('zonecpu')

    @task_method
    def zonevfs_setup(self):
        self._zone_setup('zonevfs')

    def zonememory_context(self):
        return self._zone_context('zonememory')

    def zonecpu_context(self):
        return self._zone_context('zonecpu')

    def zonevfs_context(self):
        return self._zone_context('zonevfs')


Collectd().as_tasks()
