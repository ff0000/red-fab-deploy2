import api
import gunicorn
import manage
import nginx
import postgres
import utils
import servers
import python
import redis

from fabric.api import env

env.platform = 'amazon'