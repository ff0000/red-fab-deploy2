from fabric.api import env

platform = 'ubuntu'

if not env.get('platform'):
    env.platform = 'ubuntu'
