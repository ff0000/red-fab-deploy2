import os

from fabric.api import env

from fab_deploy2 import *
from fab_deploy2.joyent import *

setup_env(os.path.abspath(os.path.dirname(__file__)))
