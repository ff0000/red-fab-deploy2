from fabric.api import env

platform = 'redhat'

if not env.get('platform'):
    env.platform = 'redhat'
