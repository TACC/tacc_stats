#!/bin/bash
python setup.py bdist_rpm
cd dist
rpm -ev tacc_statsd-2.1.1
rpm -ivh tacc_statsd-2.1.1-1.x86_64.rpm
