#!/usr/bin/env python
import cPickle as pickle
import os,sys
sys.path.append('@CONFIG_PY_DIR@')
import job_stats
from numpy import *
import subprocess

TEST_PASSED = True

pickle_file = open(sys.argv[1],'r')
new = pickle.load(pickle_file)
pickle_file.close()

pickle_file = open(sys.argv[2],'r')
old = pickle.load(pickle_file)
pickle_file.close()

if new.id != old.id:
    print 'Job IDs differ between new and old'
    TEST_PASSED = False
    
if not array_equal(new.times,old.times):
    print 'Time records differ between new and old'
    TEST_PASSED = False

for host_name, new_host in new.hosts.iteritems():

    if host_name in old.hosts:
        old_host = old.hosts[host_name]
    else: 
        print 'host_name',host_name,'has been added'
        TEST_PASSED = False
        continue
    
    for type_name, new_type_stats in new_host.stats.iteritems():

        if type_name in old_host.stats:
            old_type_stats = old_host.stats[type_name]
        else:
            print 'type_name',type_name,'has been added'
            TEST_PASSED = False
            continue

        for dev, new_dev_stats in new_type_stats.iteritems():
            if dev in old_type_stats:
                old_dev_stats = old_type_stats[dev]
            else: 
                print 'dev',dev,'has been added'
                TEST_PASSED = False
                continue

            if array_equal(new_dev_stats.ravel(),old_dev_stats.ravel()): 'test passed'
            else: 
                print 'test failed due to difference in',type_name,dev
                #print 'new',new_dev_stats
                #print 'old',old_dev_stats
                TEST_PASSED = False

try:
    subprocess.call('rm @CMAKE_CURRENT_BINARY_DIR@/python/' + new.id, shell=True)

except: pass
print TEST_PASSED
