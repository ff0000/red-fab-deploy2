
.. toctree::

Introduction
============

*red-fab-deploy2* is a collection of `Fabric <http://www.fabfile.org/>`_ scripts
for deploying and managing projects created at `RED <http://www.ff0000.com/>`_.
License is MIT.

This project is specifically targeted at deploying websites built using
the `generator-red-django <https://github.com/ff0000/generator-red-django/>`_
project creation tool.

These tools are being geared towards deploying on `Joyent <http://www.joyent.com>`_
but can be extended to be used on other providers and platforms.

Main features
--------------

* Provisioning servers based on the following stack components:

  * PostgreSQL

  * Redis

  * nginx

  * Django

  * gunicorn

  * HAproxy

  * Celery


* Deployment code to *development*, *staging* and *production* environments.

* Start and stop services on remote servers.

* Creating backups for databases.
