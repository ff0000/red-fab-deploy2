.. toctree::

Installation
============

IMPORTANT: red-fab-deploy 2will only work if you install the following packages:

``$ pip install -e git+git://github.com/bitprophet/fabric.git#egg=fabric``

To use the joyent provider you will need smartdc

``$ pip install smartdc``

For amazon you will need boto.

Deployment and Setup
====================

Fabfile

The first thing you need to do is set up your fabfile. This file should import * from fab_deploy. As well as specify which provider this setup is for. You do this by import * from that package. For example:

``from fab_deploy2.joyent import *``

Server Configs

In your projects deploy folder there should be a file named servers.ini. This file keeps track of the different types of servers and any relationships between them. As you add servers using this tool the file will be updated. You also configure firewalls using this file by specifing which ports should be open to which other roles.

Fabric roles are also setup based on the information in this file. So adding -R app-server for example will run your specifed command on all servers in that section of the config file.

Tasks

To list the tasks run fab --list. Running fab -d task_name will print the full docstring for the given task.
