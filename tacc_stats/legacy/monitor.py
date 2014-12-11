from __future__ import print_function

def import_test():
    try:
        from tacc_stats import monitor
    except ImportError,e:
        print(e,"Failed!!!")
        assert False
    print("Loaded",monitor.__name__,"successfully")
    assert monitor.__name__

