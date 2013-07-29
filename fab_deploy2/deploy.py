import os

from fabric.api import local, env, task, cd, run
from fabric.decorators import runs_once

from fab_deploy2 import functions
@task(hosts=[])
def deploy(branch=None, update_configs=False):
    """
    Deploy this project.

    Internally calls the update task for on the server for each
    host. After all are finished calls restart services for
    each host.

    Takes an optional branch argument that can be used
    to deploy a branch other than master.
    """

    role = env.host_roles.get(env.host_string)
    if role:
        task_name = "servers.{0}.update".format(
                            env.role_name_map.get(role))
    else:
        raise Exception("Don't know how to deploy this host")

    functions.execute_on_host(task_name, branch=branch,
                              update_configs=update_configs)
    if env.host_string == env.hosts[-1]:
        task_name = "servers.{0}.restart_services".format(
                            env.role_name_map.get(role))
        functions.execute_on_host(task_name)
