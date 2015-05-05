.. toctree::

Installation
============

This section describes how to install *red-fab-deploy2* on your computer.

First, you need to make sure you already have `pip <https://pip.pypa.io/en/stable/installing.html>`_
installed on your computer.

Then, you'll need to install *Fabric* Python package as follows:

``$ pip install Fabric``

If *Joyent* is your cloud provider then you must install the required package for it:

``$ pip install smartdc``

If you prefer *Amazon* as provider then you must install *boto* package using the
following command:

``$ pip install boto``

Once you have installed all required Python packages, you'll be able to install
*red-fab-deploy2* executing the following command:

``$ pip install red-fab-deploy2``
