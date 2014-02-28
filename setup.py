#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

setup = None
try:
    from setuptools import setup as setuptools
    setup = setuptools
except ImportError:
    from distutils.core import setup as distutils
    setup = distutils


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

required = ['redis', 'gevent']
py_modules = ['zenircbot_api']

setup(
    name='zenircbot_api',
    version='2.2.5',
    description='API for ZenIRCBot',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('HISTORY.rst').read()),
    author='Wraithan (Chris McDonald)',
    author_email='xwraithanx@gmail.com',
    url='http://zenircbot.rtfd.org/',
    py_modules=py_modules,
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=required,
    license=open('LICENSE').read(),
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ),
)
