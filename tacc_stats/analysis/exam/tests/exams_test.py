from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.exam as exams

### Test exams
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'1835740_ref')] * 3

#### Maximum Packet Rate Test
def packetrate_test():
    print("PacketRate Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.PacketRate,threshold=0)
    aud.run(filelist)
    aud.test()
    assert (aud.results['PacketRate'].values().count(True)) == 1

#### Mean Packet Size Test
def packetsize_test():
    print("PacketSize Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.PacketSize,threshold=10000)
    aud.run(filelist)
    aud.test()
    assert (aud.results['PacketSize'].values().count(True)) == 1

#### Max Memory Usage Test
def memusage_test():
    print("MemUsage Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemUsage,threshold=100)
    aud.run(filelist)
    aud.test()
    assert (aud.results['MemUsage'].values().count(True)) == 1

#### CPI Test
def cpi_test():
    print("HighCPI Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.HighCPI,threshold=0.01)
    aud.run(filelist)
    aud.test()
    assert (aud.results['HighCPI'].values().count(True)) == 1

#### Node Imbalance
def imb_test():
    print("Imbalance Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Imbalance,threshold=0.01)
    aud.run(filelist)
    aud.test()
    assert (aud.results['Imbalance'].values().count(True)) == 1

#### Idle
def idle_test():
    print("Idle Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Idle,threshold=0.01)
    aud.run(filelist)
    aud.test()
    assert (aud.results['Idle'].values().count(True)) == 1

#### Catastrophic
def cat_test():
    print("Catastrophe Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Catastrophe,threshold=10)
    aud.run(filelist)
    aud.test()
    assert (aud.results['Catastrophe'].values().count(True)) == 1

#### Low FLOPS test
def flops_test():
    print("Low Flops Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.LowFLOPS,threshold=10e6)
    aud.run(filelist)
    aud.test()
    assert (aud.results['LowFLOPS'].values().count(True)) == 1


#### Memory Bandwidth
def mbw_test():
    print("Memory Bandwidth Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemBw,threshold=0.1)
    aud.run(filelist)
    aud.test()
    assert (aud.results['MemBw'].values().count(True)) == 1

#### Metadata Rate
def mdr_test():
    print("MetaData Rate Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MetaDataRate,threshold=0.1)
    aud.run(filelist)
    aud.test()
    assert (aud.results['MetaDataRate'].values().count(True)) == 1


