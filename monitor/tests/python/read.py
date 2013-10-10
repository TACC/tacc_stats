#!/usr/bin/env python
import cPickle as pickle
import os,sys
sys.path.append('@CONFIG_PY_DIR@')
import job_stats
pickle_file = open(sys.argv[1],'r')
a = pickle.load(pickle_file)
pickle_file.close()
print 'Jobid',a.id
print 'Recorded Times',a.times
print 

for host_name, host in a.hosts.iteritems():
    print host_name
    print '## Cores - 1 per core'
    print 'intel_snb', 'Schema:', a.get_schema('intel_snb').desc
    for dev, stats in host.stats['intel_snb'].iteritems(): 
        print dev
        print stats

    print
    print '## Cache Boxes - 8 per socket'
    print 'intel_snb_cbo', 'Schema:', a.get_schema('intel_snb_cbo').desc
    for dev, stats in host.stats['intel_snb_cbo'].iteritems(): 
        print dev
        print stats

    print
    print '## Power Control Units - 1 per socket'
    print 'intel_snb_pcu', 'Schema:',a.get_schema('intel_snb_pcu').desc
    for dev, stats in host.stats['intel_snb_pcu'].iteritems(): 
        print dev
        print stats

    print
    print '## Home Agent Units - 1 per socket'
    print 'intel_snb_hau','Schema:', a.get_schema('intel_snb_hau').desc
    for dev, stats in host.stats['intel_snb_hau'].iteritems(): 
        print dev
        print stats

    print
    print 'Memory Controllers - 4 per socket'
    print 'intel_snb_imc','Schema:',a.get_schema('intel_snb_imc').desc
    for dev, stats in host.stats['intel_snb_imc'].iteritems(): 
        print dev
        print stats

    print
    print 'Ring-to-PCI Unit - 1 per socket'
    print 'intel_snb_r2pci','Schema:',a.get_schema('intel_snb_r2pci').desc
    for dev, stats in host.stats['intel_snb_r2pci'].iteritems(): 
        print dev
        print stats

    print
    print 'QPI Unit - 1 per socket'
    print 'intel_snb_qpi','Schema:',a.get_schema('intel_snb_qpi').desc
    for dev, stats in host.stats['intel_snb_qpi'].iteritems(): 
        print dev
        print stats


    print
    print 'ib sw'
    print 'ib_sw','Schema:',a.get_schema('ib_sw').desc
    for dev, stats in host.stats['ib_sw'].iteritems(): 
        print dev
        print stats
