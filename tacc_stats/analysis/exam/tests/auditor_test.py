from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.exam as exams

### Test exams
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'1835740_ref')]*3
filelist.extend([os.path.join(os.path.dirname(os.path.abspath(__file__)),'3620_ref')]*3)
### Auditor Test
def auditors_test():
    print('Auditor Test')
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemUsage, min_time=0)
    aud.stage(exams.PacketRate, min_time=0)
    aud.stage(exams.PacketSize, min_time=0)

    aud.run(filelist)

    aud.test(exams.MemUsage,threshold=1000)
    aud.test(exams.PacketRate,threshold=0)
    aud.test(exams.PacketSize,threshold=1.0e3)

    assert (aud.results['MemUsage'].values().count(True)) ==  2
    assert (aud.results['PacketRate'].values().count(True)) ==  2
    assert (aud.results['PacketSize'].values().count(True)) ==  2

