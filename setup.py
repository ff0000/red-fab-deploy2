#!/usr/bin/env python
from distutils.core import setup
import re
import os


base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fab_deploy2'))
data_files = []
for dirpath, dirnames, filenames in os.walk(os.path.join(base_path, 'default-configs')):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    files = [os.path.join(dirpath, f)[len(base_path)+1:] \
                            for f in filenames if not f.endswith('.pyc')]
    data_files.extend(files)

setup(
    name = 'red-fab-deploy2',
    packages=[
        'fab_deploy2',
        'fab_deploy2.base',
        'fab_deploy2.local',
        'fab_deploy2.joyent',
        'fab_deploy2.operating_systems',
        'fab_deploy2.operating_systems.ubuntu',
        'fab_deploy2.operating_systems.redhat',
        'fab_deploy2.operating_systems.smartos',
        'fab_deploy2.joyent',
        'fab_deploy2.joyent.smartos',
        'fab_deploy2.joyent.ubuntu',
        'fab_deploy2.amazon',
        'fab_deploy2.amazon.ubuntu',
        'fab_deploy2.amazon.redhat',
        'fab_deploy2.rackspace',
        'fab_deploy2.rackspace.ubuntu',
        'fab_deploy2.rackspace.redhat',
		],
	version = '0.2.4',
    author='RED Interactive Agency',
    author_email='geeks@ff0000.com',
    include_package_data=True,
    package_data={
        'fab_deploy2': data_files
    },

    url='http://www.github.com/ff0000/red-fab-deploy2/',
    download_url = 'http://www.github.com/ff0000/red-fab-deploy2/',

    license = 'MIT license',
    description = """ Code deployment tool """,

    long_description = """ Code deployment tool """,
    install_requires = ["fabric",
                        "jinja2",
                        "smartdc",
                        "boto"],
	dependency_links = [],

    classifiers = (
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
