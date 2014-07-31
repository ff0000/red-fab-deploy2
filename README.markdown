# red-fab-deploy: django deployment tool

red-fab-deploy is a collection of Fabric scripts for deploying and
managing projects created at RED. License is MIT.

This project is specifically targeted at deploying websites built using
the generator-red-django project creation tool.

These tools are being geared towards deploying on Joyent but can be extended to be used on other providers.

## Installation

IMPORTANT: red-fab-deploy will only work if you install the following packages:

	$ pip install fabric

To use the joyent provider you will need smartdc

    $ pip install smartdc

## Deployment and Setup

### Fabfile

The first thing you need to do is set up your fabfile. This file should import * from the flavor you want to use. The basic structure provider.os. For example:

    from fab_deploy2.joyent.smartos import *

### Server Configs

In your projects deploy folder there should be a file named servers.ini. This file keeps track of the different types of servers and any relationships between them. As you add servers using this tool the file will be updated. You also configure firewalls using this file by specifing which ports should be open to which other roles.

Fabric roles are also setup based on the information in this file. So adding -R app-server for example will run your specifed command on all servers in that section of the config file.

### Overriding behavior

In many cases you will want to customize the behavior of a certain task. For this reason most tasks are implemented as context task classes. You can inherit from the task that you want to customize, make your changes and then in your fabfile override that task name with your new class. See the docs for more information.

### Tasks

To list the tasks run fab --list. Running fab -d task_name will print the full docstring for the given task.
