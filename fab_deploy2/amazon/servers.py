import sys
import importlib
from fabric.api import env
from fabric.tasks import Task

from fab_deploy2 import functions
from fab_deploy2.base import servers as base_servers
from fab_deploy2.tasks import task_method

from api import get_ec2_connection

from boto.ec2.elb.healthcheck import HealthCheck

class AmazonAppServerMixin(object):
    """
    App server that tells nginx to allow proxy for headers from
    all internal ips because we don't know
    what the amazon lb will be
    """

    def get_context(self):
        context = base_servers.BaseServer.get_context(self)
        default = {
            'nginx' : { 'lbs' : ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'] }
        }
        return functions.merge_context(context, default)

class LBServer(base_servers.LBServer):
    """
    Set up load balancer

    Create an elastic load balancer, read connections info from server.ini,
    get ip address and look for corresponding ec2 instances, and register
    the instances with load balancer.

    you may define the following optional arguments in env:
    * **lb_name**:  name of load_balancer. If not defined, load balancer will
                    be named after the name of your project directory.
    * **listeners**:  listeners of load balancer, a list of tuple
                      (lb port, instance port, protocol).
                      If not provided, only port 80 will be registered.
    * **hc_policy**:  a dictionary defining the health check policy, keys can be
                      interval, target, healthy_threshold, timeout
                      and unhealthy_threshold

                      default value is
                          hc_policy = {
                            'interval': 30,
                            'target':   'HTTP:80/index.html', }
    """

    name = 'lb_server'
    config_section = 'load-balancer'

    hc_policy = {
                'interval': 30,
                'target':   'HTTP:80/', }

    listeners =  [(80, 80, 'http',)]

    def get_context(self):
        default = {
            'hc_policy' : self.hc_policy,
            'listeners' : self.listeners,
            'lb_name' : env.project_name
        }
        context = env.context.get(self.config_section, {})
        return functions.merge_context(context, default)

    def _update_server(self, **kwargs):
        conn = get_ec2_connection(server_type='ec2', **kwargs)
        elb_conn = get_ec2_connection(server_type='elb', **kwargs)

        zones = [ z.name for z in conn.get_all_zones()]
        context = self.get_context()

        lb_name = context.get('lb_name')
        listeners = context.get('listeners')

        connections = env.config_object.get_list('app-server',
                                                 env.config_object.CONNECTIONS)

        instances = set(self.get_instance_id_by_connections(connections))
        if len(instances) == 0:
            print "Cannot find any ec2 instances match your connections"
            sys.exit(1)

        elb = self._get_elb(elb_conn, lb_name)
        print "find load balancer %s" %lb_name
        if not elb:
            elb = elb_conn.create_load_balancer(lb_name, zones, listeners)
            print "load balancer %s successfully created" %lb_name


        elb_instances = set([x.id for x in elb.instances])
        to_remove = elb_instances - instances
        to_add = instances - elb_instances

        if to_add:
            elb.register_instances(to_add)
            print "register instances into load balancer"
            print to_add

        if to_remove:
            print "remove instances from load balancer"
            print to_remove
            elb.deregister_instances(list(to_remove))

        hc_policy = context.get('hc_policy')
        if not hc_policy:
            hc_policy = self.hc_policy
        print "Configure load balancer health check policy"
        hc = HealthCheck(**hc_policy)
        elb.configure_health_check(hc)

    @task_method
    def setup(self, **kwargs):
        self._update_server(**kwargs)

    @task_method
    def update(self, **kwargs):
        self._update_server(**kwargs)

    @task_method
    def restart_services(self):
        pass

    def _remove_servers(self, servers):
        self._reset_config_object(servers)
        self._update_server()

    def get_instance_id_by_connections(self, connections, **kwargs):
        """
        get ec2 instance id based on ip address
        """
        ips = set([ ip.split('@')[-1] for ip in connections])
        instances = []
        conn = get_ec2_connection(server_type='ec2', **kwargs)
        reservations = conn.get_all_instances()
        for resv in reservations:
            for instance in resv.instances:
                if instance.ip_address in ips or instance.public_dns_name in ips:
                    instances.append(instance.id)
        return instances

    def _get_elb(self, conn, lb_name):
        lbs = conn.get_all_load_balancers()
        for lb in lbs:
            if lb.name == lb_name:
                return lb
        return None
