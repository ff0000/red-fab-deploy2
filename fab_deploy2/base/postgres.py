import os
import sys
import time

from fabric.api import run, sudo, env, local, hide, settings
from fabric.contrib.files import append, sed, exists, contains
from fabric.context_managers import prefix
from fabric.operations import get, put
from fabric.context_managers import cd

from fabric.tasks import Task

from fab_deploy2 import functions
from fab_deploy2.functions import random_password
from fab_deploy2 import functions
from fab_deploy2.tasks import ServiceContextTask, task_method

class Postgresql(ServiceContextTask):
    """
    Install postgresql on server

    install postgresql package;
    enable postgres access from localhost without password;
    enable all other user access from other machines with password;
    setup a few parameters related with streaming replication;
    database server listen to all machines '*';
    create a user for database with password.
    """
    context_name = 'postgresql'

    postgres_config = {
        'listen_addresses':  "'*'",
        'wal_level':         "hot_standby",
        'wal_keep_segments': "32",
        'archive_timeout':   "130200",
        'max_wal_senders':   "5",
        'archive_mode':      "on"
    }

    default_context = {
        'data_dir_default_base' : '/var/pgsql',
        'binary_path' : None,
        'user' : 'postgres',
        'group' : 'postgres',
        'version_directory_join' : '.',
        'cron_file' : '/etc/crontab',
        'keep_wals' : 3,
        'version' : '9.3',
        'backup_path' : '/backups/dbs',
        'pw_encryption' : 'md5',
        'trigger' : '/tmp/pg_failover_trigger',
        'package_path' : None,
        'utils' : 'utils'
    }

    @task_method
    def setup_backups(self, path=None, **kwargs):
        if not path:
            path = self.backup_path

        script = os.path.join(env.configs_dir, 'pg_backup.sh')
        sudo('mkdir -p %s' % path)
        sudo('chown {0}:{1} {2}'.format(self.user, self.group, path))

        online_path = os.path.join(path, 'pg_backup.sh')
        put(script, online_path, use_sudo=True)
        sudo('sed -i s#BACKUPDIR=.*#BACKUPDIR=%s#g %s' % (path, online_path))
        sudo('chmod +x %s' % online_path)

        bash = run('which bash')
        append('/tmp/pg_cron','0 0 * * *         %s %s' % (bash, online_path))
        run('sudo su {0} -c "crontab < /tmp/pg_cron"'.format(self.user))

    @task_method
    def master_setup(self, db_version=None, **kwargs):
        if db_version:
            env.task_context['version'] = db_version

        self._install_package()
        self._setup_hba_config()
        self._setup_postgres_config()
        self._setup_archive_dir()

        self._start_db_server()
        self._setup_ssh_key()
        self._create_user()
        self._create_replicator()
        self._add_monitoring()

    @task_method
    def start(self):
        self._start_db_server()

    @task_method
    def stop(self):
        self._stop_db_server()

    @task_method
    def slave_setup(self, master=None, **kwargs):
        self._install_package()
        self._stop_db_server()

        self._setup_ssh_key()

        self._prep_slave(master, full_sync=True)

        self._setup_hba_config()
        self._setup_archive_dir()

        self._start_db_server()
        self._add_monitoring()

    @task_method
    def promote_slave(self):
        """
        Promote given slave to master. Touches trigger file and updates
        config without restarting the server.
        """
        sudo('touch {0}'.format(self.trigger))
        self._setup_postgres_config(hot_standby='off')

    @task_method
    def update(self):
        self._setup_hba_config()
        self._setup_postgres_config()
        self._setup_archive_dir()

    @task_method
    def update_slave(self, master=None, full_sync=False):
        """
        Updates the replication relation configuration on a slave.

        If you specify full_sync=True then data will be rynced from
        master. Otherwise only the configs are updated.
        """
        if not master:
            print "Please provide the required argument master."
            sys.exit(1)

        if full_sync:
            self._stop_db_server()

        self._prep_slave(master, full_sync=full_sync)
        self._start_db_server()

    @task_method
    def replication_status(self):
        run('echo "SELECT pg_is_in_recovery();" | sudo su {0} -c psql'.format(self.user))
        run('echo "select now() - pg_last_xact_replay_timestamp() AS replication_delay;" | sudo su {0} -c psql'.format(self.user))

    @task_method
    def create_user(self, user=None):
        self._create_user(user=user)

    @task_method
    def create_db(self, db_name=None, user=None):
        user = self._get_username(user=user)
        while not db_name:
            db_name = raw_input("Enter your database name: ")

        db_name = db_name.replace(' ', '')
        run('sudo su {0} -c "createdb -O {1} -E UNICODE {2}"'.format(self.user, user, db_name))

    def _add_monitoring(self):
        functions.execute_if_exists('collectd.install_plugin', 'postgresql')

    def _install_package(self):
        raise NotImplementedError()

    def _stop_db_server(self):
        raise NotImplementedError()

    def _start_db_server(self):
        raise NotImplementedError()

    @property
    def db_version(self):
        version = self.version
        return self.version_directory_join.join(version.split('.')[:2])

    @property
    def home_dir(self):
        if not env.task_context.get('home_dir'):
            env.task_context['home_dir'] = self._get_home_dir()
        return env.task_context['home_dir']

    def _get_home_dir(self):
        output = run('grep {0} /etc/passwd | cut -d: -f6'.format(self.user))
        return output.stdout

    @property
    def data_dir(self):
        if not env.task_context.get('data_dir'):
            env.task_context['data_dir'] = self._get_data_dir()
        return env.task_context['data_dir']

    def _get_data_dir(self):
        output = run('echo $PGDATA')
        if output.stdout and exists(output.stdout, use_sudo=True):
            return output.stdout

        data_path = self.data_dir_default_base
        data_version_path = os.path.join(data_path, 'data%s' % self.db_version)
        if exists(data_version_path, use_sudo=True):
            return data_version_path
        else:
            return os.path.join(data_path, 'data')

    @property
    def config_dir(self):
        if not env.task_context.get('config_dir'):
            env.task_context['config_dir'] = self._get_config_dir()
        return env.task_context['config_dir']

    def _get_config_dir(self):
        return self.data_dir

    def _setup_parameter(self, filename, **kwargs):
        for key, value in kwargs.items():
            origin = "#%s =" %key
            new = "%s = %s" %(key, value)
            sudo('sed -i "/%s/ c\%s" %s' %(origin, new, filename))

    def _setup_hba_config(self):
        """
        enable postgres access without password from localhost
        """
        hba_conf = os.path.join(self.config_dir, 'pg_hba.conf')
        if exists(hba_conf, use_sudo=True):
            context = self.get_template_context()
            functions.render_template("postgresql/pg_hba.conf", hba_conf,
                                      context=context, use_sudo=True)
            sudo('chown {0}:{1} {2}'.format(self.user, self.group, hba_conf))
        else:
            print ('Could not find file %s. Please make sure postgresql was '
                   'installed and data dir was created correctly.'% hba_conf)
            sys.exit(1)

    def _setup_postgres_config(self, **extra_kwargs):
        config = dict(self.postgres_config)
        config['archive_command'] = ("'cp %s %s/wal_archive/%s'"
                                                   %('%p', self.data_dir, '%f'))
        config.update(extra_kwargs)

        postgres_conf = os.path.join(self.config_dir, 'postgresql.conf')

        if exists(postgres_conf, use_sudo=True):
            self._setup_parameter(postgres_conf, **config)
        else:
            print ('Could not find file %s. Please make sure postgresql was '
                   'installed and data dir was created correctly.' %postgres_conf)
            sys.exit(1)

    def _setup_wal_cron(self, wal_dir):
        append('{0}'.format(self.cron_file),
               '0 4 * * * root find {0}* -type f -mtime +{1} -delete'.format(
                                    wal_dir, self.keep_wals), use_sudo=True)

    def _setup_archive_dir(self):
        archive_dir = os.path.join(self.data_dir, 'wal_archive')
        sudo("mkdir -p {0}".format(archive_dir))
        sudo("chown {0}:{1} {2}".format(self.user, self.group, archive_dir))
        self._setup_wal_cron(archive_dir)
        return archive_dir

    def _setup_ssh_key(self):
        ssh_dir = os.path.join(self.home_dir, '.ssh')

        rsa = os.path.join(ssh_dir, 'id_rsa')
        if exists(rsa, use_sudo=True):
            print "rsa key exists, skipping creating"
        else:
            sudo('mkdir -p %s' %ssh_dir)
            sudo('chown -R {0}:{1} {2}'.format(self.user, self.group, ssh_dir))
            sudo('chmod -R og-rwx %s' %ssh_dir)
            run('sudo su {0} -c "ssh-keygen -t rsa -f {1} -N \'\'"'.format(self.user, rsa))

    def _get_username(self, user=None):
        if not user:
            section = env.host_roles.get(env.host_string)
            if env.config_object.has_option(section, env.config_object.USERNAME):
                user = env.config_object.get(section, env.config_object.USERNAME)

        if not user:
            user = raw_input("Now we are creating the database user, please "
                             "specify a username: ")

        while user == self.user:
            user = raw_input("Sorry, you are not allowed to use your root user "
                                 "as username, please choose another one: ")
        return user

    def _create_user(self, user=None):
        time.sleep(2)
        user = self._get_username(user=user)
        db_out = run('echo "select usename from pg_shadow where usename=\'%s\'" |'
                     'sudo su %s -c psql' % (user, self.user))
        if user in db_out:
            print 'user %s already exists, skipping creating user.' %user
        else:
            run("sudo su {0} -c 'createuser -D -S -R -P {1}'".format(self.user, user))

        section = env.host_roles.get(env.host_string)
        if section:
            env.config_object.set(section, env.config_object.USERNAME, user)

        return user

    def _get_replicator_pass(self):
        try:
            password = env.config_object.get('db-server',
                                             env.config_object.REPLICATOR_PASS)
            return password
        except:
            print ("I can't find replicator-password from db-server section "
                   "of your server.ini file.\n Please set up replicator user "
                   "in your db-server, and register its info in server.ini")
            sys.exit(1)

    def _create_replicator(self):
        section = env.host_roles.get(env.host_string)
        db_out = run("echo '\du replicator' | sudo su {0} -c 'psql'".format(self.user))
        if 'replicator' not in db_out:
            replicator_pass = random_password(12)

            if section and env.config_object.has_option(section,
                            env.config_object.REPLICATOR_PASS):
                pw = env.config_object.get(section,
                            env.config_object.REPLICATOR_PASS)
                if pw:
                    replicator_pass = pw


            c1 = ('CREATE USER replicator REPLICATION LOGIN ENCRYPTED '
                  'PASSWORD \"\'%s\'\"' %replicator_pass)
            run("echo {0} | sudo su {1} -c \'psql\'".format(c1, self.user))
            history_file = os.path.join(self.home_dir, '.psql_history')
            if exists(history_file):
                sudo('rm %s' %history_file)

            if section:
                env.config_object.set(section, env.config_object.REPLICATOR,
                                      'replicator')
                env.config_object.set(section, env.config_object.REPLICATOR_PASS,
                                      replicator_pass)
            return replicator_pass
        else:
            print "user replicator already exists, skipping creating user."
            return None

    def _prep_slave(self, master, full_sync=True):
        results = functions.execute_on_platform('utils.get_ip', None, hosts=[master])
        master_ip = results[master]
        assert master_ip

        if full_sync:
            self._sync_from_master(master)

        self._setup_postgres_config(hot_standby='on')
        self._setup_recovery_conf(master_ip)

        with settings(warn_only=True):
            sudo('rm {0}'.format(self.trigger))

    def _sync_from_master(self, master):
        self._ssh_key_exchange(master, env.host_string)
        results = functions.execute_on_platform('utils.get_ip', None)
        slave_ip = results[env.host_string]
        assert slave_ip

        with settings(host_string=master):
            run('echo "select pg_start_backup(\'backup\', true)" | sudo su postgres -c \'psql\'')
            run('sudo su postgres -c "rsync -av --exclude postmaster.pid '
                '--exclude pg_xlog --exclude server.crt '
                '--exclude server.key '
                '%s/ postgres@%s:%s/"'%(self.data_dir, slave_ip, self.data_dir))
            run('echo "select pg_stop_backup()" | sudo su postgres -c \'psql\'')

    def _setup_recovery_conf(self, master_ip):
        context = self.get_template_context()

        psql_bin = ''
        if self.binary_path:
            psql_bin = self.binary_path

        wal_dir = os.path.join(self.data_dir, 'wal_archive')
        recovery_conf = os.path.join(self.data_dir, 'recovery.conf')

        if psql_bin:
            pg_archive = '{0}pg_archivecleanup'.format(psql_bin)
        else:
            pg_archive = run('which pg_archivecleanup')

        context[self.context_name]['wal_dir'] = wal_dir
        context[self.context_name]['pg_archive'] = pg_archive
        context['master_ip'] = master_ip
        context['replication_pw'] = self._get_replicator_pass()

        functions.render_template("postgresql/recovery.conf", recovery_conf,
                                  context=context, use_sudo=True)
        sudo('chown {0}:{1} {2}'.format(self.user, self.group, recovery_conf))

    def _trust_key(self, addr, known):
        with settings(warn_only=True):
            result = sudo('ssh-keyscan -H {0} >> {1}'.format(addr, known))
            if result.return_code != 0:
                result = sudo('ssh-keyscan {0} >> {1}'.format(addr, known))

    def _ssh_key_exchange(self, master, slave):
        """
        copy ssh key(pub) from master to slave, so that master can access slave
        without password via ssh
        """
        ssh_dir = os.path.join(self.home_dir, '.ssh')
        known = os.path.join(ssh_dir, 'known_hosts')

        with settings(host_string=master):
            rsa_pub = os.path.join(ssh_dir, 'id_rsa.pub')
            pub_key = sudo('cat %s' %rsa_pub)
            slave_addr = slave.split('@')[1]
            self._trust_key(slave_addr, known)
            sudo('chown {0}:{1} {2}'.format(self.user, self.group, known))

        with settings(host_string=slave):
            authorized_keys = os.path.join(ssh_dir, 'authorized_keys')
            if not exists(authorized_keys):
                sudo('touch {0}'.format(authorized_keys))

            sudo('chown {0}:{1} {2}'.format(self.user, self.group, authorized_keys))

            append(authorized_keys, pub_key, use_sudo=True)
            results = functions.execute_on_platform('utils.get_ip', None, hosts=[master])
            master_ip = results[master]
            self._trust_key(master_ip, known)
            sudo('chown {0}:{1} {2}'.format(self.user, self.group, known))
