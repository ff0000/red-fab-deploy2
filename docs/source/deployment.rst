.. toctree::

Deployment
===========

Main task for deployment code from local machine to remote server is called *deploy*.
This task accepts a *git* branch or *commit* hash as argument. The code will be deployed
from local machine where task is executed to remote machine. This means all files will be
*rsync* from local machine to remote machine.


Every time we deploy code, a new directory will be created on the remote machine. This
directory will be called as the hash specified for the *deploy* task. If we are using
the name of the branch, then the directory will be called as hash which matches with
given branch.

Let's imagine we want to deploy *develop* branch which hash is *d009e1cbd47af63bfd6f964352f428e7d43109a98*,
then a new directory called *d009e1* will be created on the remote machine. As you noticed,
only the first six characters of the hash will be used.

Also, *deploy* tasks use a *symlink* to pointing to the new created folder. This folder
will be served by *nginx* and *gunicorn* and *symlink* will be updated every time we deploy
new code.

Keep in mind that *nginx* configuration file is not updated every *deploy* task
is executed. If you need to do that, don't forget to run *nginx.update* task. However,
*Django* settings file is updated every time *deploy* is launched.


Tasks
-----

Here you find a few interesting tasks related to deployments.

Deploying *develop* branch to *dev-server* role:

``$ fab deploy:develop -R dev-server``

Deploying *master* branch to *app-server* without changing *symlink*:

``$ fab deploy:branch=master,no_restart=True -R app-server``

For more examples, see :doc:`cookbook`


Templates
---------

When a server is being provisioned a set of pre-defined templates are used. All
of them can be found on *fab_deploy2/default-configs/templates* directory. Obviously,
you can create your own templates for your custom requirements.

If you need to create your own templates, *red-fab-deploy2* is using the following
conventions:

- *deploy/templates/*: This is the base directory for your templates.

- *deploy/templates/django/*: It contains templates for your Django *settings*. Each template file must use as name same one that role defined by *servers.ini* file.

- *deploy/templates/nginx/*: Templates for *nginx* web server configuration.

- *deploy/requirements/*: This directory contains *pip* requirements file for each environment, not related to role.
