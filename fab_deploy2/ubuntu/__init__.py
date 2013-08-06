import celery
import gunicorn
import nginx
import postgres
import servers
import python
import redis

from fabric.api import env

env.platform = 'ubuntu'