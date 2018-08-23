#!/usr/bin/env python
from setuptools import setup, find_packages
import os
from configparser import ConfigParser

DISTNAME = 'tacc_stats'
LICENSE = 'LGPL'
AUTHOR = "Texas Advanced Computing Center"
EMAIL = "rtevans@tacc.utexas.edu"
URL = "http://www.tacc.utexas.edu"
DOWNLOAD_URL = 'https://github.com/TACC/tacc_stats'
VERSION = "2.3.3"

DESCRIPTION = ("A job-level performance monitoring and analysis package for \
High Performance Computing Platforms")
LONG_DESCRIPTION = """
TACC Stats unifies and extends the measurements taken by Linux monitoring utilities such as systat/SAR, iostat, etc.~and resolves measurements by job and hardware device so that individual job/applications can be analyzed separately.  It also provides a set of analysis and reporting tools which analyze TACC Stats resource use data and flags jobs/applications with low resource use efficiency.
"""

scripts=[
    'tacc_stats/analysis/job_printer.py',
    'tacc_stats/site/manage.py',
    'tacc_stats/site/machine/update_db.py',
    'tacc_stats/pickler/job_pickles.py',
    'tacc_stats/pickler/sacct_gen.py',
    'tacc_stats/listend.py'
    ]

config = ConfigParser()
config.read("tacc_stats.ini")

with open("tacc_stats/cfg.py", 'w') as fd:
    for s in config.sections():
        for key, val in dict(config.items(s)).items():
            fd.write(key + " = " + "\"" + val + "\"" + '\n')

setup(
    name = DISTNAME,
    version = VERSION,
    maintainer = AUTHOR,
    maintainer_email = EMAIL,
    description = DESCRIPTION,
    license = LICENSE,
    url = URL,
    download_url = DOWNLOAD_URL,
    long_description = LONG_DESCRIPTION,
    packages = find_packages(),
    package_data = {'tacc_stats' : ['cfg.py']},
    include_package_data = True,
    scripts = scripts,
    install_requires = ['argparse','numpy','matplotlib', 'psycopg2-binary',
                        'bokeh', 'django', 'python-hostlist', 'PyMySQL',
                        'mysql-connector-python', 'python-memcached'],
    platforms = 'any',
    classifiers = [
        'Development Status :: 5 - Production',
        'Environment :: Console',
        'Operating System :: Linux',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
    ]
)
