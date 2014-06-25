from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis as gen

### Test gen

jobs = ["3556052","3558133","3561011","1","3558643"]



def ld_test():
    ld = gen.LariatData(directory='.',daysback=3)        
    for job in jobs:
        ld.set_job(job,end_time='2014-06-22')
        assert job in ld.ld_json
        if job == "1": 
            assert ld.id == 0 and not ld.ld_json[job][0]

    print('--------------------------')

    ld = gen.LariatData(directory='.',daysback=3)        
    for job in jobs:        
        ld.set_job(job,end_time=1403413200)
        assert job in ld.ld_json
        if job == "1": 
            assert ld.id == 0 and not ld.ld_json[job][0]
