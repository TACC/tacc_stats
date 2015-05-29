from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.exam as exams

### Test exams
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'1835740_ref')] * 3
filelist.extend([os.path.join(os.path.dirname(os.path.abspath(__file__)),'3620_ref')]*3)

#### VecPercent
def vecpercent_test():
    print("VecPercent Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.VecPercent,min_time=0)
    aud.run(filelist)
    aud.test(exams.VecPercent,threshold=30)
    assert (aud.results['VecPercent'].values().count(True)) == 1

#### GigE bandwidth
def gige_bw_test():
    print("GigEBW Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.GigEBW,min_time=0)
    aud.run(filelist)
    aud.test(exams.GigEBW,threshold=0)
    assert (aud.results['GigEBW'].values().count(True)) == 2

#### Maximum Packet Rate Test
"""
def gigepacketrate_test():
    print("GigEPacketRate Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.GigEPacketRate,threshold=0)
    aud.run(filelist)
    aud.test()
    assert (aud.results['GigEPacketRate'].values().count(True)) == 1
"""
#### Maximum Packet Rate Test
def packetrate_test():
    print("PacketRate Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.PacketRate,min_time=0)
    aud.run(filelist)
    aud.test(exams.PacketRate,threshold=0)
    assert (aud.results['PacketRate'].values().count(True)) == 2

#### Mean Packet Size Test
def packetsize_test():
    print("PacketSize Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.PacketSize,min_time=0)
    aud.run(filelist)
    aud.test(exams.PacketSize,threshold=10000)
    assert (aud.results['PacketSize'].values().count(True)) == 2

#### Max Memory Usage Test
def memusage_test():
    print("MemUsage Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemUsage,min_time=0)
    aud.run(filelist)
    aud.test(exams.MemUsage,threshold=100)
    assert (aud.results['MemUsage'].values().count(True)) == 2

#### CPI Test
def cpi_test():
    print("HighCPI Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.HighCPI,min_time=0)
    aud.run(filelist)
    aud.test(exams.HighCPI,threshold=0.01)
    assert (aud.results['HighCPI'].values().count(True)) == 2

#### Node Imbalance
def imb_test():
    print("Imbalance Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Imbalance,min_time=0)
    aud.run(filelist)
    aud.test(exams.Imbalance,threshold=0.01)
    assert (aud.results['Imbalance'].values().count(True)) == 1

#### Idle
def idle_test():
    print("Idle Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Idle,min_time=0, min_hosts=1)
    aud.run(filelist)
    aud.test(exams.Idle,threshold=0.01)
    assert (aud.results['Idle'].values().count(True)) == 1

#### Catastrophic
def cat_test():
    print("Catastrophe Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.Catastrophe,min_time=0,min_hosts=1)
    aud.run(filelist[0:3])
    aud.test(exams.Catastrophe,threshold=10)
    assert (aud.results['Catastrophe'].values().count(True)) == 1

#### Low FLOPS test
def flops_test():
    print("Low Flops Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.LowFLOPS,min_time=0)
    aud.run(filelist)
    aud.test(exams.LowFLOPS,threshold=10e6)
    assert (aud.results['LowFLOPS'].values().count(True)) == 1


#### Memory Bandwidth
def mbw_test():
    print("Memory Bandwidth Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MemBw,min_time=0)
    aud.run(filelist)
    aud.test(exams.MemBw,threshold=0.0)
    assert (aud.results['MemBw'].values().count(True)) == 2

#### Metadata Rate
def mdr_test():
    print("MetaData Rate Test")
    aud = exams.Auditor(processes=1)
    aud.stage(exams.MetaDataRate,min_time=3600)
    aud.run(filelist[0:3])
    aud.test(exams.MetaDataRate,threshold=0.1)
    assert (aud.results['MetaDataRate'].values().count(True)) == 1


