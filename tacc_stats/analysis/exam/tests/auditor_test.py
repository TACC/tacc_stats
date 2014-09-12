from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.exam as exams

### Test exams
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'1835740_ref')]*3

### Auditor Test
def auditors_test():
    print('Auditor Test')
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemUsage,threshold=1000)
    aud.stage(exams.PacketRate,threshold=0)
    aud.stage(exams.PacketSize,threshold=1.0e3)

    aud.run(filelist)
    aud.test()
    
    assert (aud.results['MemUsage'].values().count(True)) ==  1
    assert (aud.results['PacketRate'].values().count(True)) ==  1
    assert (aud.results['PacketSize'].values().count(True)) ==  1

