#!/usr/bin/env python

import os.path
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setupconf = dict(
    name="pyZabbixSender",
    py_modules=[
        "txZabbixSender",
        "pyZabbixSender",
        "pyZabbixSenderBase",
    ],
    author="Kurt Momberg",
    author_email="kurtqm@yahoo.com.ar",
    description="Python implementation of zabbix_sender.",
    long_description = read('README.md'),
    url="https://github.com/kmomberg/pyZabbixSender",
    version="0.1",
    license = "GNU GPL v2",
#    packages = find_packages(),
#    install_requires = [???],
    classifiers = [
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Environment :: Library",
        "Framework :: Zabbix",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.5.1",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: System :: Monitoring",
    ],
    zip_safe=False,
)

if __name__ == '__main__':
    setup(**setupconf)
