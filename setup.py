#!/usr/bin/env python
from setuptools import setup, find_packages
import os
from ConfigParser import ConfigParser

DISTNAME = 'tacc_stats'
LICENSE = 'LGPL'
AUTHOR = "Texas Advanced Computing Center"
EMAIL = "rtevans@tacc.utexas.edu"
URL = "http://www.tacc.utexas.edu"
DOWNLOAD_URL = 'https://github.com/TACC/tacc_stats'
VERSION = "2.3.0"

DESCRIPTION = ("A job-level performance monitoring and analysis package for \
High Performance Computing Platforms")
LONG_DESCRIPTION = """
TACC Stats unifies and extends the measurements taken by Linux monitoring utilities such as systat/SAR, iostat, etc.~and resolves measurements by job and hardware device so that individual job/applications can be analyzed separately.  It also provides a set of analysis and reporting tools which analyze TACC Stats resource use data and flags jobs/applications with low resource use efficiency.
"""

scripts=[
    'tacc_stats/analysis/job_sweeper.py',
    'tacc_stats/analysis/job_plotter.py',
    'tacc_stats/analysis/job_printer.py',
    'tacc_stats/site/manage.py',
    'tacc_stats/site/machine/update_db.py',
    'tacc_stats/site/machine/update_thresholds.py',
    'tacc_stats/site/machine/thresholds.cfg',
    'tacc_stats/pickler/job_pickles.py',
    'tacc_stats/pickler/job_pickles_slurm.py',
    'tacc_stats/listend.py'
    ]

config = ConfigParser()
config.read("tacc_stats.ini")

with open("tacc_stats/cfg.py", 'w') as fd:
    for s in config.sections():
        print s
        for key, val in dict(config.items(s)).iteritems():
            print key,val
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
    setup_requires = ['nose'],
    install_requires = ['argparse','numpy','matplotlib','scipy','django'],
    test_suite = 'nose.collector',
    platforms = 'any',
    classifiers = [
        'Development Status :: 5 - Production',
        'Environment :: Console',
        'Operating System :: Linux',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Scientific/Engineering',
    ]
)
