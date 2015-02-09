import sys
import time

from fabric.api import env, execute
from fabric.tasks import Task

from fab_deploy2 import functions

from smartdc import DataCenter

DEFAULT_PACKAGE = 'g3-standard-1.75-kvm'
DEFAULT_DATASET = 'sdc:sdc:base64'

class New(Task):
    """
    Provisions and sets up a new joyent server.

    Uses the joyent API for provisioning a new server. In order
    to run this task your fabfile must contain a line like:

    ``joyent_account = 'account_name'``

    Takes the following arguments:

    * **dataset**: The name of the joyent data set you want to use.
             Defaults to Small 1GB.

    * **server_size**: The size server you want. Defaults to smartos64.

    * **type**: Required. The type of server you are provisioning. This
          should correspond to a setup task. If no such task is
          found an error will be raised.

    * **data_center**: The datacenter to provision this server in.
                 If not provided your env will be checked for
                 joyent_default_data_center if that does not exist
                 either an error will be raised.

    You will be prompted to enter your ssh key name, this should correspond
    with the name that was used when your key was registered with this joyent
    account.

    Once your machine is provisioned and ready (this can take up to 10 mins).
    The setup task you provided will be run.

    Please note that care should be taken when running this command to make
    sure that too many machines are not created. If an error occurs while
    waiting for the machine to be ready or while running the setup task
    this command should not be run again or another machine will be provisioned.
    Rememeber setup tasks can be executed directly.

    This is a serial task and should not be called with any hosts
    as the provisioned server ends up being the remote host.
    """

    name = 'add_server'
    serial = True

    def run(self, **kwargs):
        """
        """
        assert not env.hosts
        if not env.get('joyent_account'):
            print "To use the joyent api you must add a joyent_account value to your env"
            sys.exit(1)

        setup_name = 'servers.%s.setup' % kwargs.get('type')
        config_name = 'servers.%s.api_config' % kwargs.get('type')
        user = kwargs.get('user', 'admin')

        task = functions.get_task_instance(setup_name)

        default_dataset = DEFAULT_DATASET
        default_package = DEFAULT_PACKAGE
        networks = None

        if task:
            results = execute(config_name, hosts=['fake'])['fake']
            config_section = results['config_section']
            if 'dataset' in results:
                default_dataset = results['dataset']
            if 'server_size' in results:
                default_package = results['server_size']
            if 'networks' in results:
                networks = results['networks']
        else:
            print "I don't know how to add a %s server" % kwargs.get('type')
            sys.exit(1)

        assert config_section
        location = kwargs.get('data_center')
        if not location and env.get('joyent_default_data_center'):
            location = env.joyent_default_data_center
        elif not location:
            print "You must supply an data_center argument or add a joyent_default_data_center attribute to your env"
            sys.exit(1)

        if not networks and env.get('joyent_default_networks'):
            networks = env.joyent_default_networks

        key_name = raw_input('Enter your ssh key name: ')
        key_id = '/%s/keys/%s' % ( env.joyent_account, key_name)
        allow_agent = env.get('allow_agent', False)
        sdc = DataCenter(location=location, key_id=key_id, allow_agent=allow_agent)

        name = functions.get_remote_name(None, config_section,
                                         name=kwargs.get('name'))

        dataset = kwargs.get('data_set', default_dataset)
        datasets = sdc.datasets(search=dataset)
        datasets = sorted(datasets, key=lambda k: k['urn'])

        if datasets:
            dataset_id = datasets[-1]['id']
        else:
            print "couldn't find a dataset %s. Here is what we found." % dataset
            print datasets
            sys.exit(1)

        package = kwargs.get('package', default_package)
        packages = sdc.packages(name=package)
        if len(packages) != 1:
            print "couldn't find a package %s. Here is what we found." % package
            print packages
            sys.exit(1)
        else:
            package_id = packages[0]['id']

        new_args = {
            'name' : name,
            'dataset' : dataset_id,
            'metadata' : kwargs.get('metadata', {}),
            'tags' : kwargs.get('tags', {}),
            'package' : package_id,
            'networks' : networks
        }

        machine = sdc.create_machine(**new_args)
        print 'waiting for machine to come up'
        machine.poll_until('running')

        public_ip = machine.public_ips[0]
        print "added machine %s" % public_ip
        host_string = '%s@%s' % (user, public_ip)
        print 'done'

        execute(setup_name, hosts=[host_string])

add_server = New()
