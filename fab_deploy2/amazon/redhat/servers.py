from fab_deploy2.amazon import servers as amazon_servers
from fab_deploy2.operating_systems.redhat.servers import *

LBServer = amazon_servers.LBServer

class AppServer(amazon_servers.AmazonAppServerMixin, AppServer):
    setup_collectd = False
    pass

AppServer().as_tasks(name="app_server")
LBServer().as_tasks(name="lb_server")
