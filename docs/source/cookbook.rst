.. toctree::

Cookbook
==========

Here you find a set of useful *red-fab-deploy2* tasks classified by recipes.

Provisioning a development server
---------------------------------

``$ fab servers.dev_server.setup -R dev-server``

Provisioning a specific development server
------------------------------------------

``$ fab servers.dev_server.setup -H user@192.168.0.1``

Deploying code to development server
------------------------------------

``$ fab deploy:develop-R dev-server``


Deploying code to production
----------------------------

``$ fab deploy:master -R app-server``


Updating configuration for nginx
----------------------------------

``$ fab nginx.update -R dev-sever``

Starting/restarting nginx
--------------------------

``$fab nginx.start -R dev-server``

Installing redis
-----------------

::

   $ fab redis.setup -R dev-server
   $ fab redis.start -R dev-server


Installing HAproxy as load-balancer
-----------------------------------

::

   haproxy.setup -R load-balancer
   haproxy.start -R load-balancer


Configuring firewall
----------------------

``$ fab firewall.setup``


Deploying without linking code and without restarting services
---------------------------------------------------------------

``$ fab deploy:branch=develop,no_restart=True -R dev-server``


Linking code and restarting services
-------------------------------------

``$ fab link_and_restart -R dev-server``

Deploying code, applying DB changes and restarting services
------------------------------------------------------------

From local machine:

``$ fab deploy:branch=develop,no_restart=True -R dev-server``

SSH remote machine:

``$ python manage.py syncdb``

From local machine:

::

   $ fab nginx.update -R dev-server
   $ fab link_and_restart -R dev-server


Using a different cache size for nginx
---------------------------------------

If you want to use a different cache size for *nginx*, you'll need to modify
the *context* variable inside your *fabfile.py*. This variable will be used by
*nginx* template for generating the final configuration file for the web server.
For example, let's replace default value used inside default template for *128m*,
only for *dev-server* servers:

::

   env.context['dev-server'] = {
      'nginx': {
        'cache_size': '128m',
    },
   }

Using roundrobin for HAproxy load balancer
-----------------------------------

::

   env.context['load-balancer'] = {
    'haproxy': {
        'balance': 'roundrobin',
    }
   }
