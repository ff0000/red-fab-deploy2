.. toctree::

How to use it on your projects
==============================

If you want to use *red-fab-deploy2* for your projects, you'll need to follow
some basic steps for configuring your project.

Fabfile
-------

The first thing you need to do is set up your *Fabric* file, which is called
*fabfile.py* and it should reside on the *root* folder of your project. Minimum
configuration for *fabfile.py* should include two differente lines:

1. Importing basic *red-fab-deploy2* components.

2. Importing specific *red-fab-deploy2* components for your cloud provider.

For example, if you cloud provider is *Joyent* the minimum configuration for your
*fabfile.py* will be the following lines:

::

   from fab_deploy2 import *
   from fab_deploy2.joyent.smartos import *

Server Configuration
---------------------

*red-fab-deploy2* has the ability of provisioning your servers for different
environments. In order to do that, *red-fab-deploy2* reads a configuration file,
which includes information related to each kind of servers. The mentioned
configuration file is called *servers.ini* and *red-fab-deploy2* looks for it
inside a directory called *deploy*, which must be located at same level that
your *root* directory.

Each section inside *deploy/servers.ini* file should contain a set of properties
related to each kind of servers. Main properties for each section are the
following ones:

- **connections**: Public URIs for connecting to server or servers through **SSH** protocol.

- **interal-ips**: Private URIs for connecting to server or servers through **SSH** protocol.

- **open-ports**: List of open ports. The specific task for setting the firewall will only open given ports by this property.

- **git-sync**: If value for this property is *true* then code will be able to get deployed on the given server or servers.

- **allowed-sections**: Sections list for servers that can be establish a connection with section servers where this property is included.

Let's suppose we need to configure 2 different servers for production environment.
The specific section will contain the following lines on your *deploy/servers.ini*:

::

    [app-server]
    connections = user@192.168.1.1, user@192.168.1.2
    internal-ips = user@10.0.1.1, user@10.0.1.2
    open-ports= 80
    restricted-ports = 8000
    git-sync = true


*red-fab-deploy2* uses the name of each section inside *servers.ini* as a specific
role for each task. This means we can run a *Fabric* command using the *-R* argument
for executing tasks only for given kind of servers. For example, if we want to
deploy code to our servers on production, we only need to execute the following
command:

``$ fab deploy:master -R app-server``

The following lines define a database server which allows to servers included in
*app-server* to connect to it:

::

   [db-server]
   connections = user@192.168.0.110
   internal-ips = 10.0.01
   allowed-sections = app-server,db-server


Tasks
-----

*red-fab-deploy2* includes *Fabric* tasks for provisioning servers, deploying code,
starting and stoping services and for creating backups. You can see a list of all
included tasks running the next command:

``$ fab --list``

Custom tasks
************

You can write your own customized tasks using those provided by *red-fab-deploy2*.
Most of them are written as classes so you can create new ones throught inheritance.
