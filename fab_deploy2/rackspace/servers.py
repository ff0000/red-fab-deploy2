from fabric.api import env, sudo
from fabric.context_managers import settings
from fabric.contrib.files import exists, append

from fab_deploy2 import functions
from fab_deploy2.base import servers as base_servers

class RSServerMixin(object):
    """
    Mixin used for all rackspace servers.

    Turns off snmp and on firewall.
    Mounts the ext3 extension on installation.

    Since rackspace likes you to do everything as root
    will a password. Does not do our normal ssh secuirty
    changes.
    """

    setup_snmp = False
    setup_firewall = True

    def _mount_device(self, device, mount_point, args=None, fs='ext3', do_format=True):
        if not args:
            args = 'defaults,noatime,nofail'

        if not exists(mount_point):
            sudo('mkdir -p {0}'.format(mount_point))

        mounted = None
        with settings(warn_only=True):
            mounted = sudo('mount | grep {0}'.format(device))

        if not mounted:
            if do_format:
                sudo('mkfs -t {0} {1}'.format(fs, device))

            append('/etc/fstab',
                   '{device}          {mount_point}  {fs}    {args}      0'.format(
                        device=device,
                        fs=fs,
                        mount_point=mount_point,
                        args=args
                   ),
                   use_sudo=True)
            sudo('mount {0}'.format(mount_point))

    def _secure_ssh(self):
        # Rackspace makes wants you do everything as root.
        # Grumble, grumble, grumble

        # For some reason RS decided not to mount the data drive
        # on it's performence servers, so mount if asked to
        context = self.get_context()
        mount_point = context.get('mount_point', getattr(self, 'mount_point', None))
        device = context.get('device', getattr(self, 'device', None))

        if mount_point and device:
            self._mount_device(device, mount_point)

class RSAppServerMixin(RSServerMixin):
    """
    App server that tells nginx to allow proxy for headers from
    all internal ips because we don't know
    what the rackspace lb will be
    """

    def get_context(self):
        context = base_servers.BaseServer.get_context(self)
        default = {
            'nginx' : { 'lbs' : ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'] }
        }
        return functions.merge_context(context, default)
