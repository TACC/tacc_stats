from __future__ import print_function
import os, sys, subprocess, glob
import tacc_stats.analysis.job_sweeper as sweeper

### Test plotters
filedir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def sweeper_test():
    args ={'a': True, 'end': '2014-05-12', 'plot': False, 'o': '.', 'N': 1, 'p': 1, 's': 0, 't': 0.0, 'test': 'HighCPI', 'start': '2014-05-12', 'dir': filedir, 'waynesses': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32],'ignore_status' : []}

    failed = sweeper.main(**args)
    assert len(failed) == 1

