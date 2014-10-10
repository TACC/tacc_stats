import os,sys,pwd
import cPickle as pickle
import tacc_stats.pickler.job_stats as job
from tacc_stats.analysis.gen import tspl,tspl_utils

p = pickle.load(open(sys.argv[1]))

for hostname,host in p.hosts.iteritems():
    for typename,t in host.stats.iteritems():
        for dev,data in t.iteritems():
            print typename,dev

