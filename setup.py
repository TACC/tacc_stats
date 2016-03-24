#!/usr/bin/env python
from setuptools import setup, find_packages
import os
import ConfigParser

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

config = ConfigParser.ConfigParser()
cfg_filename = os.path.abspath('setup.cfg')
config.read(cfg_filename)
filename = os.path.join(os.path.dirname(__file__), 'tacc_stats', 'cfg.py')
print '\n--- Configure Web Portal Module ---\n'
with open(filename, 'w') as fd:
    for name, path in dict(config.items('PORTAL_OPTIONS')).iteritems():
        print name,'=', path
        fd.write(name + " = " + "\"" + path + "\"" + "\n")
    fd.write("seek = 0\n")        

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
    include_package_data = True,
    package_data = { 'tacc_stats' : ['cfg.py'] },
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
