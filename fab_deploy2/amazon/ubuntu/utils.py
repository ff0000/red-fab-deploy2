from fabric.api import task, run

from fab_deploy2.operating_systems.ubuntu.utils import *
from fab_deploy2.amazon import utils as amazon_utils

get_ip = task(amazon_utils.get_ip)
