import celery
import gunicorn
import nginx
import postgres
import servers
import python
import redis
import utils

from fabric.api import env


env.platform = 'redhat'
