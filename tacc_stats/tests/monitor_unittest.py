from __future__ import print_function
import os, sys

def load():
    from tacc_stats import monitor
    print("TESTING IF MONITOR PACKAGE IS LOADED>>>>>>>>>>>>>>>>>>>")
    assert monitor
