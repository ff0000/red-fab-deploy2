from fabric.api import env

platform = 'joyent'

if not env.get('platform'):
    env.platform = 'joyent'
