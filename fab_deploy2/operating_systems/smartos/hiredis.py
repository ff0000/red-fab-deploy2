import os

from fab_deploy2 import functions
from fab_deploy2.tasks import ContextTask

from fabric.api import run, sudo, settings
from fabric.contrib.files import exists
from fabric.context_managers import cd

class HiRedisSetup(ContextTask):
    """
    Setup hiredis
    """

    context_name = 'hiredis'
    default_context = {
        'package_name' : 'libhiredis-dev'
    }
    name = "setup"

    def run(self):
        if not exists('/opt/local/lib/libhiredis.so.0.10'):
            run('wget --no-check-certificate http://github.com/redis/hiredis/archive/v0.11.0.tar.gz -O v0.11.0.tar.gz')
            run('tar -xvf v0.11.0.tar.gz')

            with cd ('hiredis-0.11.0'):
                run('gcc -std=c99 -pedantic -c -O3 -fPIC  -Wall -W -Wstrict-prototypes -Wwrite-strings -std=c99 net.c')
                run('gcc -std=c99 -pedantic -c -O3 -fPIC  -Wall -W -Wstrict-prototypes -Wwrite-strings -std=c99 hiredis.c')
                run('gcc -std=c99 -pedantic -c -O3 -fPIC  -Wall -W -Wstrict-prototypes -Wwrite-strings -std=c99 sds.c')
                run('gcc -std=c99 -pedantic -c -O3 -fPIC  -Wall -W -Wstrict-prototypes -Wwrite-strings -std=c99 async.c')
                run('gcc -shared -Wl,-soname -Wl,libhiredis.so.0.10 -o libhiredis.so net.o hiredis.o sds.o async.o')

            for d in ['/opt/local/gcc47', '/opt/local']:
                if exists(d):
                    sudo('mkdir -p {0}/include/hiredis'.format(d))
                    sudo('cp hiredis-0.11.0/hiredis.h {0}/include/hiredis/'.format(d))
                    sudo('cp hiredis-0.11.0/async.h {0}/include/hiredis/'.format(d))
                    sudo('cp hiredis-0.11.0/libhiredis.so {0}/lib/libhiredis.so.0.10'.format(d))
                    sudo('ln -sf /opt/local/lib/libhiredis.so.0.10 {0}/lib/libhiredis.so'.format(d))
                    sudo('ln -sf /opt/local/lib/libhiredis.so.0.10 {0}/lib/libhiredis.so.0'.format(d))

            with settings(warn_only=True):
                result = run('crle | grep /opt/local/lib/')
                if result.return_code != 0:
                    sudo('crle -l /lib:/usr/lib:/opt/local/lib')

setup = HiRedisSetup()
