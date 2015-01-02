#!/usr/bin/env python
from distutils.core import setup
import re
import os

"""
Some methods were grabbed from:
http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy

"""
def parse_requirements(file_name):
	requirements = []
	for line in open(file_name, 'r').read().split('\n'):
		if re.match(r'(\s*#)|(\s*$)', line):
			continue
		if re.match(r'\s*-e\s+', line):
			requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
		elif re.match(r'\s*-f\s+', line):
			pass
		else:
			requirements.append(line)

	return requirements

def parse_dependency_links(file_name):
	dependency_links = []
	for line in open(file_name, 'r').read().split('\n'):
		if re.match(r'\s*-[ef]\s+', line):
			dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))

	return dependency_links

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
	version = '0.2.3',
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

    long_description = open('README.markdown').read(),
    install_requires = parse_requirements('requirements.txt'),
	dependency_links = parse_dependency_links('requirements.txt'),

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
