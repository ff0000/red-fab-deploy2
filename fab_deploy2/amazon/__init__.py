import api
import gunicorn
import manage
import nginx
import postgres
import utils
import servers
import python
import redis
import celery

from fabric.api import env

env.platform = 'amazon'