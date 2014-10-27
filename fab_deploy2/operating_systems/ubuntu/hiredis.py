import os

from fab_deploy2 import functions
from fab_deploy2.tasks import ContextTask

from fabric.api import run, sudo

class HiRedisSetup(ContextTask):
    """
    Setup hiredis
    """

    context_name = 'hiredis'
    default_context = {
        'package_name' : 'libhiredis-dev'
    }
    name = "setup"

    def run(self):
        functions.execute_on_host('utils.install_package', package_name=self.package_name)

setup = HiRedisSetup()
