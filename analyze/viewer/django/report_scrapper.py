"""Script for scrapping daily report from tacc_stats"""

import os
import sys
import traceback

def fill_jobs( data ):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tacc_stats.webapp.settings'
    from tacc_stats.webapp.tacc_stats.models import Job
    for d in data:
        try:
            Job(**d).save()
        except:
            print 'Exception on'
            print '='*80
            print d
            print '-'*80
            traceback.print_exc(file=sys.stdout)
            print '-'*80

def get_data_dict(filename, *args, **kws):
    """Reads the daily report file and returns data as a list of dictionaries"""
    with open(filename) as fp:
        first_line = fp.readline()
        dict_keys = first_line[1:].strip().split()
        dict_keys = map(lambda s: s.replace('/','').replace(':','_'), dict_keys)
        dict_keys[dict_keys.index('USER')] = 'USER_FLOPS'
        items = []
        for line in fp.readlines():
            if line[0] == '+':
                items.append(dict(zip(dict_keys, line[1:].strip().split())))
        return items

def main(filename):
    fill_jobs(get_data_dict(filename))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Call with filename of report to analyse"
    else:
        main(sys.argv[1])
