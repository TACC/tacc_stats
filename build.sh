#!/bin/bash
python setup.py bdist_rpm
cd dist
rpm -ev tacc_stats-2.1.0-1
rpm -ivh tacc_stats-2.1.0-1.x86_64.rpm
