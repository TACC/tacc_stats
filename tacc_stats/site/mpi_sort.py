#!/usr/bin/env python
import sys
import cPickle as pickle

print sys.argv[1]
job_mpi_data = pickle.load(open(sys.argv[1],'rb'))

mpi_tree = {}

for key,data in job_mpi_data.iteritems():

    mpi_type = data[1]
    nodes = data[0]
    jobid = key

    try:
        mpi_tree[mpi_type].append((jobid,nodes))
    except:
        mpi_tree[mpi_type] = [(jobid,nodes)]
num_jobs = len(job_mpi_data.keys())
print 'Number of jobs:',num_jobs


print '{0: <25}{1: <10}{2: <5}'.format('MPI Flavor','# Jobs','%')
for key,data in mpi_tree.iteritems():
    print '{0: <25}{1: <10}{2: <5}'.format(key,len(data),100*len(data)/float(num_jobs))

