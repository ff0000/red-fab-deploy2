import sys, os
from fabric.api import task, run, sudo, env, local, execute, settings
from fabric.tasks import Task
from fabric.contrib.files import append, sed, exists, contains
from fabric.operations import get, put
from fabric.context_managers import cd

from fab_deploy2 import functions
from fab_deploy2.tasks import MultiTask, task_method

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

    def _add_snmp(self, config_section):
        if self.setup_snmp:
            functions.execute_on_host('snmp.setup')

    def _secure_ssh(self):
        # Change disable root and password
        # logins in /etc/ssh/sshd_config
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
                    execute('firewall.setup', hosts=env.roledefs[section])

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
        self._setup_services()
        self._add_snmp(self.config_section)
        self._update_firewalls()
        self._save_config()

        self._update_server()
        self._restart_services()

    @task_method
    def update(self, branch=None, update_configs=True):
        """
        Update server.

        Shouldn't restart services.
        Only updates config files if update_configs is true
        """
        self._update_server(branch=branch,
                            update_configs=update_configs)

    @task_method
    def restart_services(self):
        """
        Restart services
        """
        self._restart_services()

    def _setup_services(self):
        functions.execute_on_host('nginx.setup')

    def _restart_services(self):
        functions.execute_on_host('nginx.start')

    def _update_server(self, branch=None, update_configs=True):
        if not branch:
            branch = self.git_branch

        if env.get('deploy_ready') != branch:
            functions.execute_on_host('local.deploy.prep_code',
                    branch=branch)
            env.deploy_ready = branch

        functions.execute_on_host('local.deploy.deploy_code',
                branch=branch)

        if update_configs:
            functions.execute_on_host('nginx.update')


    def get_context(self):
        app_servers = env.config_object.get_list('app-server',
                                          env.config_object.INTERNAL_IPS)
        default = {
            'nginx' : { 'upstream_addresses' : app_servers }
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
        raise NotImplementedError()

    def _setup_services(self):
        super(AppServer, self)._setup_services()
        functions.execute_on_host('gunicorn.setup')

    def _restart_services(self):
        super(AppServer, self)._restart_services()
        functions.execute_on_host('gunicorn.start')

    def _update_server(self, *args, **kwargs):
        super(AppServer, self)._update_server(*args, **kwargs)
        functions.execute_on_host('python.update')
        if kwargs.get('update_configs'):
            functions.execute_on_host('gunicorn.update')

    def get_context(self):
        lbs = env.config_object.get_list('load-balancer',
                                          env.config_object.INTERNAL_IPS)
        defaults = {
            'nginx' : { 'lbs' : lbs },
            'gunicorn' : { 'listen_address' : '0.0.0.0:8000' }
        }

        context = super(AppServer, self).get_context()
        return functions.merge_context(context, defaults)

class DBServer(BaseServer):
    """
    Setup a database server
    """
    name = 'db_server'
    config_section = 'db-server'

    def _setup_db(self):
        dict = functions.execute_on_host('postgres.master_setup',
                        section=self.config_section,
                        save_config=True)

    @task_method
    def setup(self):
        self._secure_ssh()
        self._set_profile()

        self._update_config(self.config_section)
        self._add_snmp(self.config_section)
        self._update_firewalls()
        self._setup_db()
        self._save_config()

    @task_method
    def context(self):
        return self.get_context()


class DBSlaveServer(DBServer):
    """
    Set up a slave database server with streaming replication
    """
    name = 'slave_db'
    config_section = 'slave-db'

    def _get_master_options(self):
        return env.config_object.get_list('db-server',
                                          env.config_object.CONNECTIONS)

    def _get_master(self):
        cons = self._get_master_options()

        n = len(cons)
        if n == 0:
            print ('I could not find db server in server.ini.'
                   'Did you set up a master server?')
            sys.exit(1)
        elif n == 1:
            master = cons[0]
        else:
            for i in range(1, n+1):
                print "[%2d ]: %s" %(i, cons[i-1])
            while True:
                choice = raw_input('I found %d servers in server.ini.'
                                   'Which one do you want to use as master? ' %n)
                try:
                    choice = int(choice)
                    master = cons[choice-1]
                    break
                except:
                    print "please input a number between 1 and %d" %n-1

        return master

    def _setup_db(self):
        master = self._get_master()
        functions.execute_on_host('postgres.slave_setup', master=master,
                                    section=self.config_section)


class DevServer(AppServer):
    """
    Setup a development server
    """
    name = 'dev_server'
    config_section = 'dev-server'
    git_branch = 'develop'

    def _setup_services(self):
        super(DevServer, self)._setup_services()
        functions.execute_on_host('postgres.master_setup',
                                  section=self.config_section)

    def get_context(self):
        # We don't want to inhert this from appserver
        return BaseServer.get_context(self)
