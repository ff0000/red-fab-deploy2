import os

from fab_deploy2.base import celery as base_celery
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import sudo, env
from fabric.contrib.files import append
from fabric.tasks import Task

class Celeryd(base_celery.Celeryd):
    pass


Celeryd().as_tasks()
