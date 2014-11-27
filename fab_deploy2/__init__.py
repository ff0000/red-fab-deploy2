import os
import sys

from fabric.api import env
from fabric import state

from config import CustomConfig

# Import all tasks
import local
from deploy import deploy, link_and_restart, migrate_db

def setup_env(project_path):
    """
    Sets up the env settings for the fabric tasks

    Checks your git repo and adds your remotes as
    aliases for those hosts. Letting you do -H web1,web2
    when you have web1 and web2 in your remotes

    Creates roles out of each section in the config file.
    Letting you do -R app-servers and that command will
    be passed to all app servers.

    Provides access to some variables that can be used through
    tasks.

    * **env.deploy_path**: the local location of the deploy folder
    * **env.project_path**: the local location of the root of your project

    * **env.base_remote_path**: the remote path where the code should be deployed
    * **env.configs_path**: the remote path where configs should be deployed

    * **env.config_object**: The servers.ini file loaded by the config parser
    * **env.conf_filename**: The path to the servers.ini file

    * **env.context**: A global context override.
    """

    # Setup fabric env
    env.deploy_path = os.path.join(project_path, 'deploy')
    env.project_path = project_path
    env.project_name = os.path.basename(env.project_path)
    env.build_dir = os.path.join(project_path, '.build')

    BASE = os.path.abspath(os.path.dirname(__file__))
    env.configs_dir = os.path.join(BASE, 'default-configs')
    env.templates_dir = os.path.join(env.configs_dir, 'templates')
    env.context = {}

    env.base_remote_path = '/srv/'
    env.configs_path = '/srv/configs/'
    env.track_static = 'project/source'


    if not env.get('current_platform'):
        env.current_platform = env.platform

    # Read the config and store it in env
    config = CustomConfig()
    env.conf_filename = os.path.abspath(os.path.join(project_path, 'deploy', 'servers.ini'))
    config.read([ env.conf_filename ])
    env.config_object = config

    # Add sections to the roledefs
    for section in config.server_sections():
        if config.has_option(section, CustomConfig.CONNECTIONS):
            env.roledefs[section] = config.get_list(section, CustomConfig.CONNECTIONS)

    env.host_roles = {}
    # Store the configs for each role
    for k,v in env.roledefs.items():
        for host in v:
            env.host_roles[host] = k
