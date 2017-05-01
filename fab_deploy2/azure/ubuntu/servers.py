from fab_deploy2.azure import servers as azure_servers
from fab_deploy2.operating_systems.ubuntu.servers import *

class ApiServer(AppMixin, azure_servers.APIServer):
    def _modify_others(self):
        pass


class IsoServer(UbuntuMixin, azure_servers.AzureIsoServer):
    pass


ApiServer().as_tasks(name="api_server")
IsoServer().as_tasks(name="iso_server")

