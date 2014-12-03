import sys, os
from fabric.api import task, run, sudo, env, local, settings
from fabric.tasks import Task
from fabric.contrib.files import append, sed, exists, contains
from fabric.operations import get, put
from fabric.context_managers import cd

from fab_deploy2 import functions
from fab_deploy2.tasks import MultiTask, task_method, PlatformCallableTask

class BaseServer(MultiTask):
    """
    Base server setup.

    Can add snmp and firewall

    Sets up ssh so root cannot login and other logins must
    be key based.
    """

    # Because setup tasks modify the config file
    # they should always be run serially.
    serial = True
    setup_firewall = True
    setup_snmp = True
    platform = None
    setup_collectd = True


    def _task_for_method(self, method):
        return PlatformCallableTask(method, self.platform, *method._task_info['args'],
                                    **method._task_info['kwargs'])

    def _get_module_obj(self, parent=None, name=None, depth=None):
        if not depth:
            depth = 0
        depth = depth + 1
        obj = super(BaseServer, self)._get_module_obj(parent=parent,
                                                       name=name,
                                                       depth=depth)
        if hasattr(self, 'config_section'):
            if not env.get('role_name_map'):
                env.role_name_map = {}
            env.role_name_map[self.config_section] = obj.__name__

        return obj

    def _set_profile(self):
        pass

    def _is_section_exists(self, section):
        if env.config_object.has_section(section):
            return True
        else:
            print "--------------------------"
            print ("Cannot find section %s. Please add [%s] into your"
                   " server.ini file." %(section, section))
            print ("If an instance has been created. You may run fab"
                   "setup.[server_type] to continue.")
            print "--------------------------"
            sys.exit(1)

    def _update_config(self, config_section):
        if not env.host_string:
            print "env.host_string is None, please specify a host by -H "
            sys.exit(1)

        self._is_section_exists(config_section)

        added = False
        cons = env.config_object.get_list(config_section,
                                env.config_object.CONNECTIONS)
        if not env.host_string in cons:
            added = True
            cons.append(env.host_string)
            env.config_object.set_list(config_section,
                                env.config_object.CONNECTIONS,
                                cons)


            ips = env.config_object.get_list(config_section,
                                env.config_object.INTERNAL_IPS)
            internal_ip = functions.execute_on_host('utils.get_ip', None)
            ips.append(internal_ip)

            env.config_object.set_list(config_section,
                                env.config_object.INTERNAL_IPS,
                                ips)
            env.roledefs[config_section].append(env.host_string)
            env.host_roles[env.host_string] = config_section
        return added

    def _save_config(self):
        env.config_object.save(env.conf_filename)

    def _setup_monitoring(self, config_section):
        if self.setup_collectd:
            self._add_collectd(self.config_section)
        elif self.setup_snmp:
            self._add_snmp(self.config_section)

    def _start_monitoring(self):
        if self.setup_collectd:
            functions.execute_on_host('collectd.start')

    def _stop_monitoring(self):
        if self.setup_collectd:
            with settings(warn_only=True):
                r = run('ps xa | grep collectd')
                if r:
                    functions.execute_on_host('collectd.stop')

    def _add_collectd(self, config_section):
        functions.execute_on_host('collectd.setup')

    def _add_snmp(self, config_section):
        if self.setup_snmp:
            functions.execute_on_host('snmp.setup')

    def _secure_ssh(self):
        # Change disable password
        # logins in /etc/ssh/sshd_config

        #disable root logins if not running as root
        user = run('whoami')
        if user != "root":
            sudo('sed -ie "s/^PermitRootLogin.*/PermitRootLogin no/g" /etc/ssh/sshd_config')
        sudo('sed -ie "s/^PasswordAuthentication.*/PasswordAuthentication no/g" /etc/ssh/sshd_config')
        self._ssh_restart()

    def _ssh_restart(self):
        raise NotImplementedError()

    def _update_firewalls(self):
        if self.setup_firewall:
            functions.execute_on_host('firewall.setup')
            # Update any section where this section appears
            for section in env.config_object.server_sections():
                if self.config_section in env.config_object.get_list(section,
                            env.config_object.ALLOWED_SECTIONS) and env.roledefs[section]:
                    functions.execute_on_platform('firewall.setup', hosts=env.roledefs[section])

    def get_context(self):
        """
        Get the role based context data for this server
        """
        return env.context.get(self.config_section, {})

    @task_method
    def api_config(self):
        return { 'config_section' : self.config_section }

class LBServer(BaseServer):
    """
    Setup a load balancer

    After base setup installs nginx. Then
    calls the deploy task.

    This is a serial task as it modifies local config files.
    """

    name = 'lb_server'

    config_section = 'load-balancer'
    git_branch = 'master'

    proxy_section = 'app-server'

    def _install_packages(self):
        pass

    @task_method
    def setup(self):
        """
        Setup server
        """
        self._secure_ssh()
        self._set_profile()

        self._update_config(self.config_section)

        self._install_packages()
        self._stop_monitoring()
        self._setup_monitoring(self.config_section)
        self._setup_services()
        self._update_firewalls()
        self._save_config()

        self._update_server()
        self._restart_services()
        self._start_monitoring()

    @task_method
    def update(self, branch=None, update_configs=True, link_code=True):
        """
        Update server.

        Shouldn't restart services.
        Only updates config files if update_configs is true
        """
        self._update_server(branch=branch,
                            update_configs=update_configs,
                            link_code=link_code)

    @task_method
    def update_code_links(self, code_hash=None):
        """
        Update server.

        Shouldn't restart services.
        Only updates config files if update_configs is true
        """
        self._link_code(code_hash=code_hash)

    @task_method
    def restart_services(self):
        """
        Restart services
        """
        self._restart_services()

    def _reset_config_object(self, servers_to_remove):
        cons = env.config_object.get_list(self.proxy_section,
                                      env.config_object.CONNECTIONS)
        internal = env.config_object.get_list(self.proxy_section,
                                      env.config_object.INTERNAL_IPS)

        indexes = []
        for server in servers_to_remove:
            if server in cons:
                indexes.append(cons.index(server))

        if not indexes:
            print "no {0} found that match {1}".format(self.proxy_section, servers)
            sys.exit(1)

        for i in indexes:
            del cons[i]
            del internal[i]

        env.config_object.set_list(self.proxy_section,
                            env.config_object.CONNECTIONS,
                            cons)
        env.config_object.set_list(self.proxy_section,
                            env.config_object.INTERNAL_IPS,
                            internal)

    def _remove_servers(self, servers):
        self._reset_config_object(servers)
        self._update_configs()
        self._restart_services()

    @task_method
    def remove_servers(self, servers=None, save=False):
        """
        Remove servers from the load balancer configuration
        """
        cons = env.config_object.get_list(self.proxy_section,
                                  env.config_object.CONNECTIONS)
        internal = env.config_object.get_list(self.proxy_section,
                                      env.config_object.INTERNAL_IPS)

        if not servers:
            n = len(cons)
            for i in range(1, n+1):
                print "[%2d ]: %s" %(i, cons[i-1])

            while True:
                choice = raw_input('I found %d servers in server.ini.'
                                   'Which one do you want to remove? ' %n)
                try:
                    servers = [cons[int(choice)-1]]
                    break
                except:
                    print "please input a number between 1 and %d" %n-1
        else:
            servers = servers.split(',')

        self._remove_servers(servers)

        if save:
            env.config_object.save(env.conf_filename)
            print 'changes were saved to server.ini'
        else:
            print 'changes were not saved to server.ini'
            env.config_object.set_list(self.proxy_section,
                                env.config_object.CONNECTIONS,
                                cons)
            env.config_object.set_list(self.proxy_section,
                                env.config_object.INTERNAL_IPS,
                                internal)

    def _setup_services(self):
        functions.execute_on_host('nginx.setup')

    def _restart_services(self):
        functions.execute_on_host('nginx.start')

    def _update_server(self, branch=None, update_configs=True, link_code=True):
        if not branch:
            branch = self.git_branch

        if env.get('deploy_ready') != branch:
            functions.execute_on_host('local.deploy.prep_code',
                    branch=branch)
            env.deploy_ready = branch

        functions.execute_on_host('local.deploy.deploy_code',
                branch=branch)

        if link_code:
            self._link_code()

        if update_configs:
            self._update_configs()


    def _link_code(self, code_hash=None):
        functions.execute_on_host('local.deploy.update_code_links',
                                   code_hash=code_hash)

    def _update_configs(self):
        functions.execute_on_host('nginx.update')

    def get_context(self):
        app_servers = env.config_object.get_list(self.proxy_section,
                                          env.config_object.INTERNAL_IPS)
        default = {
            'nginx' : { 'upstream_addresses' : app_servers },
        }
        context = super(LBServer, self).get_context()
        return functions.merge_context(context, default)

    @task_method
    def context(self):
        return self.get_context()

class AppServer(LBServer):
    """
    Setup a app-server

    Inherits from lb_setup so does everything it does.
    Also installs gunicorn, python, and other base packages.
    Runs the scripts/setup.sh script.

    This is a serial task as it modifies local config files.
    """

    name = 'app_server'
    config_section = 'app-server'

    packages = []

    def _install_packages(self):
        for package in self.packages:
            functions.execute_on_host('utils.install_package', package_name=package)

    def _setup_services(self):
        super(AppServer, self)._setup_services()
        functions.execute_on_host('gunicorn.setup')

    def _restart_services(self):
        super(AppServer, self)._restart_services()
        functions.execute_on_host('gunicorn.start')

    def _update_server(self, *args, **kwargs):
        super(AppServer, self)._update_server(*args, **kwargs)
        functions.execute_on_host('python.update')

    def _update_configs(self):
        super(AppServer, self)._update_configs()
        functions.execute_on_host('gunicorn.update')

    def get_context(self):
        lbs = env.config_object.get_list('load-balancer',
                                          env.config_object.INTERNAL_IPS)
        defaults = {
            'nginx' : { 'lbs' : lbs },
            'gunicorn' : { 'listen_address' : '0.0.0.0:8000' },
        }

        context = super(LBServer, self).get_context()
        return functions.merge_context(context, defaults)

class DBServer(BaseServer):
    """
    Setup a database server
    """
    name = 'db_server'
    config_section = 'db-server'

    def _setup_db(self):
        dict = functions.execute_on_host('postgres.master_setup')

    @task_method
    def setup(self):
        self._secure_ssh()
        self._set_profile()

        self._update_config(self.config_section)
        self._stop_monitoring()
        self._setup_monitoring(self.config_section)
        self._update_firewalls()
        self._setup_db()
        self._save_config()
        self._start_monitoring()

    @task_method
    def update(self):
        functions.execute_on_host('postgres.update')

    @task_method
    def context(self):
        return self.get_context()


class DBSlaveServer(DBServer):
    """
    Set up a slave database server with streaming replication
    """
    name = 'slave_db'
    config_section = 'slave-db'
    master_config_section = 'db-server'

    def _get_master(self):
        return functions.get_valid_host_from_conf(self.master_config_section)

    def _setup_db(self):
        master = self._get_master()
        functions.execute_on_host('postgres.slave_setup', master=master)

    def _do_promote(self, candidate):
        functions.execute_on_platform('postgres.promote_slave', hosts=[candidate])

    def _remove_pair(self, section, host_string):
        if env.config_object.has_section(self.config_section):
            cons = env.config_object.get_list(section,
                                    env.config_object.CONNECTIONS)
            internal_cons = env.config_object.get_list(section,
                                    env.config_object.INTERNAL_IPS)

            try:
                i = cons.index(host_string)
                old = cons[i]
                old_internal = internal_cons[i]

                del cons[i]
                del internal_cons[i]

                env.config_object.set_list(section,
                                    env.config_object.CONNECTIONS,
                                    cons)
                env.config_object.set_list(section,
                                    env.config_object.INTERNAL_IPS,
                                    internal_cons)
                return old, old_internal
            except ValueError:
                return None, None

    @task_method
    def update(self, master=None, full_sync=False):
        if not master:
            master = self._get_master()

        functions.execute_on_host('postgres.update_slave',
                            master=master, full_sync=full_sync)

    @task_method
    def promote(self, master=None):
        if not master:
            master = self._get_master()

        if len(env.all_hosts) > 1 or len(env.all_hosts) < 1:
            env.host_string = functions.get_valid_host_from_conf(self.config_section)

        self._do_promote(env.host_string)
        self._update_config(self.master_config_section)

        # Reset internal lookups
        env.roledefs[self.master_config_section].append(env.host_string)
        env.host_roles[env.host_string] = self.master_config_section
        if env.host_string in env.roledefs[self.config_section]:
            env.roledefs[self.config_section].remove(env.host_string)

        if master in env.host_roles:
            del env.host_roles[master]

        if master in env.roledefs[self.master_config_section]:
            env.roledefs[self.master_config_section].remove(master)

        # Remove new master from slaves
        self._remove_pair(self.config_section, env.host_string)

        # Remove old master from masters
        old_master, old_master_internal = self._remove_pair(self.master_config_section, master)
        if old_master and old_master_internal:
            if not env.config_object.has_section('defunct-master'):
                env.config_object.add_section('defunct-master')

            cons = env.config_object.get_list('defunct-master',
                            env.config_object.CONNECTIONS)
            internal = env.config_object.get_list('defunct-master',
                            env.config_object.INTERNAL_IPS)

            cons.append(old_master)
            internal.append(old_master_internal)

            env.config_object.set_list('defunct-master',
                env.config_object.CONNECTIONS,
                cons)
            env.config_object.set_list('defunct-master',
                env.config_object.INTERNAL_IPS,
                internal)
        self._save_config()

class DevServer(AppServer):
    """
    Setup a development server
    """
    name = 'dev_server'
    config_section = 'dev-server'
    git_branch = 'develop'
    setup_collectd = False

    def _setup_database(self):
        functions.execute_on_host('postgres.master_setup',
                                  section=self.config_section)

    def _setup_services(self):
        super(DevServer, self)._setup_services()
        self._setup_database()

    def get_context(self):
        # We don't want to inhert this from appserver
        return BaseServer.get_context(self)
