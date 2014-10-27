import os

from fab_deploy2.base import haproxy as base_haproxy
from fab_deploy2.tasks import task_method
from fab_deploy2 import functions

from fabric.api import run, sudo, env, local, settings
from fabric.tasks import Task

class Haproxy(base_haproxy.Haproxy):
    """
    Install nginx
    """
    rsyslog_conf = "/opt/local/etc/rsyslog.conf"

    def _install_package(self):
        functions.execute_on_host('utils.install_package', package_name='haproxy')
        # Some package versions don't include user
        with settings(warn_only=True):
            sudo("groupadd haproxy")
            sudo("useradd -g haproxy -s /usr/bin/false haproxy")

    def _setup_logging(self):
        with settings(warn_only=True):
            functions.execute_on_host('utils.install_package', package_name='rsyslog')
        sudo('svcadm disable system/system-log')

        update_conf = False
        with settings(warn_only=True):
            result = run("grep haproxy {0}".format(self.rsyslog_conf))
            if result.return_code:
                update_conf = True

        if update_conf:
            lines  = [
                "$ModLoad imudp.so",
                "$UDPServerRun 514",
                "$UDPServerAddress 127.0.0.1",
                "local1.* -{0}".format(self.logfile),
                "& ~"
            ]
            start = int(run('grep -n "ModLoad imsolaris" {0} | cut -f1 -d:'.format(self.rsyslog_conf)))

            for line in lines:
                start = start + 1
                sudo("sed -i '{0}i{1}' {2}".format(start, line, self.rsyslog_conf))
            sudo('logadm -C 3 -p1d -c -w {0} -z 1'.format(self.logfile))

            functions.execute_on_host('utils.start_or_restart', name='rsyslog',
                    host=[env.host_string])

    @task_method
    def start(self):
        functions.execute_on_host('utils.start_or_restart', name='haproxy',
                host=[env.host_string])

    @task_method
    def stop(self):
        run('svcadm disable haproxy')

Haproxy().as_tasks()
