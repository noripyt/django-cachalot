#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from cachalot import __version__


CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(CURRENT_PATH, 'requirements.txt')) as f:
    required = f.read().splitlines()


setup(
    name='django-cachalot',
    version=__version__,
    author='Bertrand Bordage, Andrew Chen Wang',
    author_email='acwangpython@gmail.com',
    url='https://github.com/noripyt/django-cachalot',
    description='Caches your Django ORM queries and automatically invalidates them.',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
    ],
    license='BSD',
    packages=find_packages(),
    install_requires=required,
    include_package_data=True,
    zip_safe=False,
)
