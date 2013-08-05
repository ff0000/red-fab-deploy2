import celery
import gunicorn
import nginx
import postgres
import servers
import python

from fabric.api import env

env.platform = 'ubuntu'