
import os, sys
import time
from ConfigParser import ConfigParser

import boto
from boto import ec2
from boto.ec2 import elb
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import HealthCheck

from fabric.api import env, execute, local
from fabric.tasks import Task

from fab_deploy2 import functions

from utils import  get_security_group


DEFAULT_AMI     = 'ami-5965401c' # ubuntu 12.04 x86_64
DEFAULT_INSTANCE_TYPE = 'm3.medium'
DEFAULT_REGION  = 'us-west-1'


def get_ec2_connection(server_type, **kwargs):
    """
    Create and return a valid connection to AWS.

    To establish a valid connection, aws_access_key and aws_secret_key have to
    be defined in a file specified by env.AWS_CREDENTIAL, with a format similar
    to server.ini file.  You should define env.AWS_CREDENTIAL in your fabfile.
    By default, this function looks into $PROJECT_DIR/deploy/amazon.ini for the
    credential information, and this file should has a section named 'amazon-aws'
    and containing lines defining aws_access_key and aws_secret_key, like below

    [amazon-aws]
    aws_access_key =
    aws_secret_key =
    """

    amzn = env.get('AWS_CREDENTIAL',
                   os.path.join(env.deploy_path, 'amazon.ini'))

    if not os.path.exists(amzn):
        print ("Cannot find environment variable AMAZON_CREDENTIALS which should"
               " point to a file with your aws_access_key and aws_secret_key info"
               " inside. You may specify it through your fab env.")
        sys.exit(1)

    parser = ConfigParser()
    parser.read(amzn)

    aws_access_key = parser.get('amazon-aws', 'aws_access_key')
    aws_secret_key = parser.get('amazon-aws', 'aws_secret_key')

    if not aws_access_key or not aws_secret_key:
        print "You must specify your amazon aws credentials to your env."
        sys.exit(1)

    region = kwargs.get('region', env.get('region'))
    if not region:
        region = DEFAULT_REGION

    if server_type == 'ec2':
        conn = ec2.connect_to_region(region,
                                     aws_access_key_id=aws_access_key,
                                     aws_secret_access_key=aws_secret_key)
        return conn
    elif server_type == 'elb':
        conn = elb.connect_to_region(region,
                                     aws_access_key_id=aws_access_key,
                                     aws_secret_access_key=aws_secret_key)
        return conn


class CreateKeyPair(Task):
    """
    Create an AWS key pair.

    This task should be run before you try to add any type of server, because
    task api.add_server will look for the key pair on your local machine.

    AWS requires a key pair to create EC2 instances, and the same key file is
    needed to login to the instances.  This task creates a key pair, and
    save its content in a file located under the same directory as
    env.AWS_CREDENTIAL file.  The key name and file location will be registered
    into the file specified by env.AWS_CREDENTIAL.

    You are responsible to keep the file in a secure place and never lose it.
    Make your own decision if you should push the key file to remote repo, or
    let git ignore it.
    """

    name = 'create_key'
    serial = True

    section = 'amazon-aws'

    def run(self, **kwargs):
        conn = get_ec2_connection(server_type='ec2', **kwargs)
        sys.stdout.write("Please give a name to the key: ")

        amzn = env.get('AWS_CREDENTIAL',
                       os.path.join(env.deploy_path, 'amazon.ini'))
        key_dir = os.path.dirname(amzn)
        while True:
            key_name = raw_input()
            key_file = os.path.join(key_dir, key_name+'.pem')
            key = conn.get_key_pair(key_name)

            if key:
                if os.path.exists(key_file):
                    print ("Looks like key file %s already exists on your "
                           "machine. I will skip creating, and just use it."
                           %key_file)
                    break
                else:
                    print ("Key '%s' already exist on AWS, but I couldn't "
                           "find it at %s. We need to create a new key, please"
                           "give a name to the key: " %(key.name, key_file))
                    continue
            else:
                key = conn.create_key_pair(key_name)
                key.save(key_dir)
                break

        parser = ConfigParser()
        parser.read(amzn)
        if not parser.has_section(self.section):
            parser.add_section(self.section)
        parser.set(self.section, 'ec2-key-name', key.name)
        parser.set(self.section, 'ec2-key-file', key_file)
        fp = open(amzn, 'w')
        parser.write(fp)
        fp.close()
        local('ssh-add %s' %key_file)


class New(Task):
    """
    Provisions and set up a new amazon AWS EC2 instance

    This task reads in a number of variables defining the properties of EC2
    instance, and create it.  Finally, if the instance is created successfully,
    this task will output its properties, and set up the instance as certain
    type of server by execute another task with the name of setup.***.

    You may provide the following parameters through command line.
    * **type**:   Required. server types, can be db_server, app_server,
                  dev_server, or slave_db
    * **region**: default is us-west-1
    * **ami_id**: AMI ID
    * **static_ip**: Set to true to use. By default this is not used.
    """

    name = 'add_server'
    serial = True

    def run(self, **kwargs):
        assert not env.hosts
        conn = get_ec2_connection(server_type='ec2', **kwargs)

        type = kwargs.get('type')
        setup_name = 'servers.%s.setup' % type
        config_name = 'servers.%s.api_config' % kwargs.get('type')

        instance_type = DEFAULT_INSTANCE_TYPE

        ami_id = kwargs.get('ami_id')
        if not ami_id:
            ami_id = DEFAULT_AMI
        user = kwargs.get('user', 'ubuntu')

        task = functions.get_task_instance(setup_name)
        if task:
            results = execute(config_name, hosts=['fake'])['fake']
            config_section = results['config_section']
            if 'instance_type' in results:
                instance_type = results['instance_type']
            if 'ami' in results:
                ami_id = results['ami']
            if 'user' in results:
                user = results['user']
        else:
            print "I don't know how to add a %s server" % type
            sys.exit(1)

        assert config_section
        amzn = env.get('AWS_CREDENTIAL',
                       os.path.join(env.deploy_path, 'amazon.ini'))

        parser = ConfigParser()
        parser.read(amzn)
        key_name = parser.get('amazon-aws', 'ec2-key-name')
        key_file = parser.get('amazon-aws', 'ec2-key-file')

        if not key_name:
            print "Sorry. You need to create key pair with create_key first."
            sys.exit(1)
        elif not os.path.exists(key_file):
            print ("I find key %s in server.ini file, but the key file is not"
                   " on its location %s. There is something wrong. Please fix "
                   "it, or recreate key pair" % (key_name, key_file))
            sys.exit(1)

        image = conn.get_image(ami_id)
        security_group = get_security_group(conn, config_section)

        name = functions.get_remote_name(None, config_section,
                                         name=kwargs.get('name'))
        SERVER = {
            'image_id':         image.id,
            'instance_type':    instance_type,
            'security_groups':  [security_group],
            'key_name':         key_name,}

        reservation = conn.run_instances(**SERVER)
        print reservation

        instance = reservation.instances[0]
        while instance.state != 'running':
            time.sleep(5)
            instance.update()
            print "...instance state: %s" % (instance.state)

        conn.create_tags([instance.id], {"Name": name})

        if not kwargs.get('static_ip', False):
            ip = instance.ip_address
        else:
            elastic_ip = conn.allocate_address()
            print "...Elastic IP %s allocated" % elastic_ip
            elastic_ip.associate(instance.id)
            ip = elastic_ip.public_ip

        print "...EC2 instance is successfully created."
        print "...wait 5 seconds for the server to be ready"
        print "...while waiting, you may want to note down the following info"
        time.sleep(5)
        print "..."
        print "...Instance using image: %s" % image.name
        print "...Added into security group: %s" %security_group.name
        print "...Instance ID: %s" % instance.id
        print "...Public IP: %s" % ip

        host_string = '{0}@{1}'.format(user, instance.public_dns_name)
        execute(setup_name, hosts=[host_string])


create_key = CreateKeyPair()
add_server = New()
