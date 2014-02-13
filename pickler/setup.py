#!/usr/bin/env python

from distutils.core import setup

setup(name='PyTaccStats',
        version='1.0',
        description='TaccStats post processing utilities for python',
        author='Bill Barth et al.',
        author_email='bbarth@tacc.utexas.edu',
        maintainer='Joseph P White',
        maintainer_email='jpwhite4@buffalo.edu',
        url='https://github.com/billbarth/tacc_stats',
        py_modules=['amd64_pmc', 'batch_acct', 'intel_snb', 'job_stats', 'sge_acct', 'torque_acct', 'slurm_stampede_acct', 'slurm_rush_acct' ],
        requires=['cStringIO', 'csv', 'datetime', 'errno', 'glob', 'gzip', 'io', 'numpy', 'os', 'subprocess', 'sys', 'time']
        )
