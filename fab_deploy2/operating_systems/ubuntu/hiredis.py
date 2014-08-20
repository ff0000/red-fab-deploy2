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
        sudo('apt-get -y install {0}'.format(self.package_name))

setup = HiRedisSetup()
