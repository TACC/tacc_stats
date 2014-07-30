from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.exam as exams

### Test exams
filelist = [os.path.join(os.path.dirname(os.path.abspath(__file__)),'1835740_ref')] * 3

#### Max Memory Usage Test
def memusage_test():
    print("MemUsage Test")
    mem_test = exams.MemUsage(processes=1,threshold=1000)
    mem_test.run(filelist)
    assert len(mem_test.failed()) == 1

#### CPI Test
def cpi_test():
    print("CPI Test")
    cpi_test = exams.HighCPI(processes=1,threshold=.01)
    cpi_test.run(filelist)
    assert len(cpi_test.failed()) == 1

#### Node Imbalance
def imb_test():
    print("Imbalance test")
    imb_test = exams.Imbalance(['intel_snb'],['LOAD_L1D_ALL'],
                               processes=1,threshold=0.01)
    imb_test.run(filelist)
    imb_test.top_jobs()
    assert len(imb_test.failed()) == 1

#### Idle
def idle_test():
    print("Idle host test")
    idle_test = exams.Idle(processes=1,threshold=0.0)
    idle_test.run(filelist)
    assert len((idle_test.failed())) == 1

#### Catastrophic
def cat_test():
    print("Catastrophic test")
    cat_test = exams.Catastrophe(processes=1,threshold=10)
    cat_test.run(filelist)
    assert len(cat_test.failed()) == 1

#### Low FLOPS test
def flops_test():
    print("Low FLOPS test")
    flops_test = exams.LowFLOPS(processes=1,threshold=1e9)
    flops_test.run(filelist)
    assert len(flops_test.failed()) == 1

#### Memory Bandwidth
def mbw_test():
    print("Memory BW test")
    bw_test = exams.MemBw(processes=1,threshold=0.1)
    bw_test.test(filelist[0])
    bw_test.run(filelist)
    assert len(bw_test.failed()) == 1 

#### Metadata Rate
def mdr_test():
    print("MetaDataRate test")
    md_test = exams.MetaDataRate(processes=1,threshold=0.1)
    md_test.run(filelist)
    assert len(md_test.failed()) == 1

