import os
import sys

from fabric.api import run, sudo, env, local, hide, settings, execute
from fabric.contrib.files import append, sed, exists, contains
from fabric.context_managers import prefix
from fabric.operations import get, put
from fabric.context_managers import cd

from fabric.tasks import Task

from fab_deploy2.functions import random_password

class PostgresInstall(Task):
    """
    Install postgresql on server

    install postgresql package;
    enable postgres access from localhost without password;
    enable all other user access from other machines with password;
    setup a few parameters related with streaming replication;
    database server listen to all machines '*';
    create a user for database with password.
    """

    name = 'master_setup'
    db_version = '9.1'

    encrypt = 'md5'
    hba_txts = ('local   all    postgres                     ident\n'
                'host    replication replicator  0.0.0.0/0   md5\n'
                'local   all    all                          password\n'
                '# # IPv4 local connections:\n'
                'host    all    all         127.0.0.1/32     %(encrypt)s\n'
                '# # IPv6 local connections:\n'
                'host    all    all         ::1/128          %(encrypt)s\n'
                '# # IPv4 external\n'
                'host    all    all         0.0.0.0/0        %(encrypt)s\n')

    postgres_config = {
        'listen_addresses':  "'*'",
        'wal_level':         "hot_standby",
        'wal_keep_segments': "32",
        'archive_timeout':   "130200",
        'max_wal_senders':   "5",
        'archive_mode':      "on" }

    data_dir_default_base = '/var/pgsql'
    binary_path = None
    version_directory_join = '.'
    cron_file = '/etc/crontab'
    keep_wals = 3

    def _get_config_dir(self, db_version, data_dir):
        return data_dir

    def _get_home_dir(self):
        output = run('grep postgres /etc/passwd | cut -d: -f6')
        return output.stdout

    def _get_data_dir(self, db_version):
        output = run('echo $PGDATA')
        if output.stdout and exists(output.stdout, use_sudo=True):
            return output.stdout

        data_path = self.data_dir_default_base
        data_version_path = os.path.join(data_path, 'data%s' %db_version)
        if exists(data_version_path, use_sudo=True):
            return data_version_path
        else:
            return os.path.join(data_path, 'data')

    def _setup_parameter(self, filename, **kwargs):
        for key, value in kwargs.items():
            origin = "#%s =" %key
            new = "%s = %s" %(key, value)
            sudo('sed -i "/%s/ c\%s" %s' %(origin, new, filename))

    def _setup_hba_config(self, config_dir, encrypt=None):
        """
        enable postgres access without password from localhost
        """

        if not encrypt:
            encrypt = self.encrypt

        hba_conf = os.path.join(config_dir, 'pg_hba.conf')
        kwargs = {'encrypt':encrypt}
        hba_txts = self.hba_txts % kwargs

        if exists(hba_conf, use_sudo=True):
            sudo("echo '%s' > %s" %(hba_txts, hba_conf))
        else:
            print ('Could not find file %s. Please make sure postgresql was '
                   'installed and data dir was created correctly.'%hba_conf)
            sys.exit(1)

    def _setup_postgres_config(self, config_dir, config):
        postgres_conf = os.path.join(config_dir, 'postgresql.conf')

        if exists(postgres_conf, use_sudo=True):
            self._setup_parameter(postgres_conf, **config)
        else:
            print ('Could not find file %s. Please make sure postgresql was '
                   'installed and data dir was created correctly.' %postgres_conf)
            sys.exit(1)

    def _setup_wal_cron(self, wal_dir):
        append('{0}'.format(self.cron_file),
               '0 4 * * * root find {0}* -type f -mtime +{1} -delete'.format(
                                    wal_dir, self.keep_wals),
               use_sudo=True)

    def _setup_archive_dir(self, data_dir):
        archive_dir = os.path.join(data_dir, 'wal_archive')
        sudo("mkdir -p %s" % archive_dir)
        sudo("chown postgres:postgres %s" % archive_dir)
        self._setup_wal_cron(archive_dir)
        return archive_dir

    def _setup_ssh_key(self):
        ssh_dir = os.path.join(self._get_home_dir(), '.ssh')

        rsa = os.path.join(ssh_dir, 'id_rsa')
        if exists(rsa, use_sudo=True):
            print "rsa key exists, skipping creating"
        else:
            sudo('mkdir -p %s' %ssh_dir)
            sudo('chown -R postgres:postgres %s' % ssh_dir)
            sudo('chmod -R og-rwx %s' %ssh_dir)
            run('sudo su postgres -c "ssh-keygen -t rsa -f %s -N \'\'"' % rsa)

    def _create_user(self, section):
        username = raw_input("Now we are creating the database user, please "
                             "specify a username: ")
        # 'postgres' is postgresql superuser
        while username == 'postgres':
            username = raw_input("Sorry, you are not allowed to use postgres "
                                 "as username, please choose another one: ")
        db_out = run('echo "select usename from pg_shadow where usename=\'%s\'" |'
                     'sudo su postgres -c psql' % username)
        if username in db_out:
            print 'user %s already exists, skipping creating user.' %username
        else:
            run("sudo su postgres -c 'createuser -D -S -R -P %s'" % username)

        env.config_object.set(section, env.config_object.USERNAME, username)

        return username

    def _create_replicator(self, db_version, section):
        db_out = run("echo '\du replicator' | sudo su postgres -c 'psql'")
        if 'replicator' not in db_out:
            replicator_pass = random_password(12)
            if env.config_object.has_option(section,
                            env.config_object.REPLICATOR_PASS):
                pw = env.config_object.get(section,
                            env.config_object.REPLICATOR_PASS)
                if pw:
                    replicator_pass = pw


            c1 = ('CREATE USER replicator REPLICATION LOGIN ENCRYPTED '
                  'PASSWORD \"\'%s\'\"' %replicator_pass)
            run("echo %s | sudo su postgres -c \'psql\'" %c1)
            history_file = os.path.join(self._get_home_dir(), '.psql_history')
            if exists(history_file):
                sudo('rm %s' %history_file)
            env.config_object.set(section, env.config_object.REPLICATOR,
                                  'replicator')
            env.config_object.set(section, env.config_object.REPLICATOR_PASS,
                                  replicator_pass)
            return replicator_pass
        else:
            print "user replicator already exists, skipping creating user."
            return None

    def _get_db_version(self, db_version):
        if not db_version:
            db_version = self.db_version
        return self.version_directory_join.join(db_version.split('.')[:2])

    def _install_package(self, db_version):
        raise NotImplementedError()

    def _restart_db_server(self, db_version):
        raise NotImplementedError()

    def _stop_db_server(self, db_version):
        raise NotImplementedError()

    def _start_db_server(self, db_version):
        raise NotImplementedError()

    def run(self, db_version=None, encrypt=None, save_config=True,
            section='db-server', **kwargs):
        """
        """
        db_version = self._get_db_version(db_version)

        self._install_package(db_version)
        data_dir = self._get_data_dir(db_version)
        config_dir = self._get_config_dir(db_version, data_dir)

        config = dict(self.postgres_config)
        config['archive_command'] = ("'cp %s %s/wal_archive/%s'"
                                                   %('%p', data_dir, '%f'))

        self._setup_hba_config(config_dir, encrypt)
        self._setup_postgres_config(config_dir, config)
        self._setup_archive_dir(data_dir)

        self._restart_db_server(db_version)
        self._setup_ssh_key()
        self._create_user(section)
        self._create_replicator(db_version, section)

        if save_config:
            env.config_object.save(env.conf_filename)


class SlaveSetup(PostgresInstall):
    """
    Set up master-slave streaming replication: slave node
    """

    name = 'slave_setup'

    postgres_config = {
        'listen_addresses': "'*'",
        'wal_level':      "hot_standby",
        'hot_standby':    "on"}

    def _get_master_db_version(self):
        output = run("psql --version | head -1 | awk '{print $3}'")
        if output.stdout:
            return self._get_db_version(output.stdout)

    def _get_replicator_pass(self):
        try:
            password = env.config_object.get_list('db-server',
                                             env.config_object.REPLICATOR_PASS)
            return password[0]
        except:
            print ("I can't find replicator-password from db-server section "
                   "of your server.ini file.\n Please set up replicator user "
                   "in your db-server, and register its info in server.ini")
            sys.exit(1)

    def _setup_recovery_conf(self, master_ip, password, data_dir):
        psql_bin = ''
        if self.binary_path:
            psql_bin = self.binary_path

        wal_dir = os.path.join(data_dir, 'wal_archive')
        recovery_conf = os.path.join(data_dir, 'recovery.conf')

        if psql_bin:
            pg_archive = '{0}pg_archivecleanup'.format(psql_bin)
        else:
            pg_archive = run('which pg_archivecleanup')

        txts = (("standby_mode = 'on'\n") +
                ("primary_conninfo = 'host=%s " %master_ip) +
                    ("port=5432 user=replicator password=%s'\n" % password) +
                ("trigger_file = '/tmp/pgsql.trigger'\n") +
                ("restore_command = 'cp -f %s/%s </dev/null'\n"
                    %(wal_dir, '%f %p')) +
                ("archive_cleanup_command = '%s %s %s'\n"
                    %(pg_archive, wal_dir, "%r")))

        sudo('touch %s' % recovery_conf)
        append(recovery_conf, txts, use_sudo=True)
        sudo('chown postgres:postgres %s' %recovery_conf)

    def _ssh_key_exchange(self, master, slave):
        """
        copy ssh key(pub) from master to slave, so that master can access slave
        without password via ssh
        """
        ssh_dir = os.path.join(self._get_home_dir(), '.ssh')

        with settings(host_string=master):
            rsa_pub = os.path.join(ssh_dir, 'id_rsa.pub')
            with hide('output'):
                pub_key = sudo('cat %s' %rsa_pub)

        with settings(host_string=slave):
            authorized_keys = os.path.join(ssh_dir, 'authorized_keys')
            with hide('output', 'running'):
                run('sudo su postgres -c "echo %s >> %s"'
                    %(pub_key, authorized_keys))

    def run(self, master=None, encrypt=None, section=None, **kwargs):
        """
        """
        if not master:
            print "Hey, a master is required for slave."
            sys.exit(1)

        results = execute('utils.get_ip', None, hosts=[master])
        master_ip = results[master]
        assert master_ip

        replicator_pass = self._get_replicator_pass()

        with settings(host_string=master):
            db_version = self._get_master_db_version()

        slave = env.host_string
        slave_ip = slave.split('@')[1]

        self._install_package(db_version)
        data_dir = self._get_data_dir(db_version)
        config_dir = self._get_config_dir(db_version, data_dir)

        self._stop_db_server(db_version)

        self._setup_ssh_key()
        self._ssh_key_exchange(master, slave)

        with settings(host_string=master):
            run('echo "select pg_start_backup(\'backup\', true)" | sudo su postgres -c \'psql\'')
            run('sudo su postgres -c "rsync -av --exclude postmaster.pid '
                '--exclude pg_xlog --exclude server.crt '
                '--exclude server.key '
                '%s/ postgres@%s:%s/"'%(data_dir, slave_ip, data_dir))
            run('echo "select pg_stop_backup()" | sudo su postgres -c \'psql\'')

        self._setup_postgres_config(config_dir, self.postgres_config)
        self._setup_archive_dir(data_dir)
        self._setup_recovery_conf(master_ip, replicator_pass,
                                  data_dir)
        self._setup_hba_config(config_dir, encrypt)

        self._start_db_server(db_version)
        print('password for replicator on master node is %s' % replicator_pass)

class Backups(Task):
    path = '/backups/dbs'
    name = 'setup_backups'

    def run(self, path=None, **kwargs):
        if not path:
            path = self.path

        script = os.path.join(env.configs_dir, 'pg_backup.sh')
        sudo('mkdir -p %s' % path)
        sudo('chown postgres:postgres %s' % path)

        online_path = os.path.join(path, 'pg_backup.sh')
        put(script, online_path, use_sudo=True)
        sudo('sed -i s#BACKUPDIR=.*#BACKUPDIR=%s#g %s' % (path, online_path))
        sudo('chmod +x %s' % online_path)

        bash = run('which bash')
        append('/tmp/pg_cron','0 0 * * *         %s %s' % (bash, online_path))
        run('sudo su postgres -c "crontab < /tmp/pg_cron"')
