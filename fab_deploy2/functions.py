import subprocess
import urlparse
import os
import random

from fabric.api import env, put, execute, run, sudo
from fabric.task_utils import crawl

from jinja2 import Environment, FileSystemLoader

import io

def get_answer(prompt):
    """
    """
    result = None
    while result == None:
        r = raw_input(prompt + ' (y or n)')
        if r == 'y':
            result = True
        elif r == 'n':
            result = False
        else:
            print "Please enter y or n"
    return result

def _command(command, shell=False):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=shell)
    o, e = proc.communicate()
    if proc.returncode > 0:
        raise Exception(e)
    return o

def call_command(*commands):
    """
    """
    return _command(commands)

def call_shell_command(command):
    """
    """
    return _command(command, shell=True)

def get_remote_name(host, prefix, name=None):
    """
    """
    assert prefix

    l = env.config_object.get_list(prefix, env.config_object.CONNECTIONS)
    i = 0
    if host in l:
        i = l.index(host)+1
    else:
        i = len(l) + 1

    return "{0}{1}".format(prefix, i)

def get_task_instance(name):
    """
    """
    from fabric import state
    return crawl(name, state.commands)

def random_password(bit=12):
    """
    generate a password randomly which include
    numbers, letters and sepcial characters
    """
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    small_letters = [chr(i) for i in range(97, 123)]
    cap_letters = [chr(i) for i in range(65, 91)]
    special = ['@', '#', '$', '%', '^', '&', '*', '-']

    passwd = []
    for i in range(bit/4):
        passwd.append(random.choice(numbers))
        passwd.append(random.choice(small_letters))
        passwd.append(random.choice(cap_letters))
        passwd.append(random.choice(special))
    for i in range(bit%4):
        passwd.append(random.choice(numbers))
        passwd.append(random.choice(small_letters))
        passwd.append(random.choice(cap_letters))
        passwd.append(random.choice(special))

    passwd = passwd[:bit]
    random.shuffle(passwd)

    return ''.join(passwd)

def merge_context(context, defaults):
    # Add defaults to context
    # without overiding anything
    for k, v in defaults.items():
        if not k in context:
            context[k] = v
        else:
            for key, val in v.items():
                if not key in context:
                    context[k][key] = v
    return context

def execute_on_host(*args, **kwargs):
    kwargs['hosts'] = [env.host_string]
    r = execute(*args, **kwargs)
    if env.host_string in r:
        return r[env.host_string]
    else:
        return r

def get_role_context(role):
    if not env.get('_role_cache'):
        env._role_cache = {}

    if not role in env._role_cache:
        task_name = "servers.{0}.context".format(
                            env.role_name_map.get(role))
        env._role_cache[role] = execute_on_host(task_name)
    return env._role_cache.get(role)

def get_context(context=None):
    if not context:
        context = {}

    context.update({
        'base_remote_path' : env.base_remote_path,
        'configs_path' : env.configs_path,
        'config' : env.config_object,
        'code_path' : os.path.join(env.base_remote_path, 'active')
    })
    return context

def template_to_string(filename, context=None):
    local_path = os.path.join(env.deploy_path, 'templates')
    platform = os.path.join(env.configs_dir, 'templates',
                            env.get('platform', 'base'))
    base = os.path.join(env.configs_dir, 'templates', 'base')
    all_templates = os.path.join(env.configs_dir, 'templates')
    search_paths = (local_path, platform, base, all_templates)

    envi = Environment(loader=FileSystemLoader(search_paths))
    context = get_context(context)
    template = (envi.get_template(filename)).render(**context)
    return template

def render_template(filename, remote_path=None, context=None):
    sudo('mkdir -p {0}'.format(env.base_remote_path))
    sudo('mkdir -p {0}'.format(env.configs_path))
    sudo('chown {0} {1}'.format(env.user, env.configs_path))
    sudo('chown {0} {1}'.format(env.user, env.base_remote_path))

    if not remote_path:
        remote_path = env.configs_path
    else:
        if not os.path.isabs(remote_path):
            remote_path = os.path.join(env.configs_path, remote_path)

    basename = os.path.basename(remote_path)
    if not basename or not '.' in basename:
        dest_path = os.path.join(remote_path, filename)
    else:
        dest_path = remote_path

    # Nake sure dir exists
    run('mkdir -p {0}'.format(os.path.dirname(dest_path)))

    # Render template
    template = template_to_string(filename, context=context)
    put(local_path=io.StringIO(template), remote_path = dest_path)
    return dest_path
