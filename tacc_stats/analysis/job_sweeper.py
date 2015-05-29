#!/usr/bin/env python
import sys,os,pwd
import operator
from datetime import datetime,timedelta
import tacc_stats.analysis.exam as exam
import tacc_stats.analysis.plot as plot
import tacc_stats.cfg as cfg
from tacc_stats.analysis.gen import tspl,tspl_utils

# Report top users by SU usage
def top_jobs(auditor,name):
    jobs = {}
    total = {}
    for jobid in auditor.metrics[name].keys():
        if not auditor.metrics[name][jobid]: continue
        acct = auditor.accts[jobid]
        try: user = pwd.getpwuid(int(acct['uid']))[0]
        except: user = acct['uid']
        sus = (acct['end_time']-acct['start_time'])*16.0/3600
        jobs.setdefault(user,[]).append((jobid, 
                                         sus,
                                         auditor.metrics[name][jobid],
                                         auditor.results[name][jobid]))
        total[user] = total.get(user,0) + sus

    sorted_totals = sorted(total.iteritems(),key=operator.itemgetter(1))
    sorted_jobs = []
    for user in sorted_totals[::-1]:
        sorted_jobs.append((user,jobs[user[0]]))
    
    return sorted_jobs


# Generate list of files for a date range and test them
def get_filelist(start,end,pickles_dir=None):
    try:
        start = datetime.strptime(start,"%Y-%m-%d")
        end   = datetime.strptime(end,"%Y-%m-%d")
    except:
        start = datetime.now() - timedelta(days=1)
        end   = start

    filelist = []
    for root,dirnames,filenames in os.walk(pickles_dir):
        for directory in dirnames:
            try:
                date = datetime.strptime(directory,'%Y-%m-%d')
                if max(date.date(),start.date()) > min(date.date(),end.date()): 
                    continue
            except:
                print directory,"does not have date format"
                continue
            filelist.extend(tspl_utils.getfilelist(os.path.join(root,directory)))

        break
    print filelist
    return filelist

def test_report(auditor, test_type):
    name = test_type.__name__

    print("---------------------------------------------")
    print(name)
    r = auditor.results[name].values()
    passed = r.count(False)
    failed = r.count(True)      
    total = passed+failed

    print("Jobs tested:",total)
    if total > 0:
        print("Percentage of jobs failed: {0:0.2f}".format(100*failed/float(total)))
    else:
        print("No jobs tested.")

    job_paths = []
    for user in top_jobs(auditor,name):        
        print("{0:10} {1:0.2f}".format(user[0][0], user[0][1]))
        test_report = ''
        for job in user[1]:
            if job[3]: 
                job_paths.append(auditor.paths[job[0]])
                test_report += "=>{0} {1:0.2f} {2:0.2f}\n".format(job[0],
                                                                  job[1],
                                                                  job[2])
        print(test_report)
    return job_paths


def main(**args):

    print args
    # Stage exams
    aud = exam.Auditor(processes=args['p'])
    for test in args['test']:
        test_type = getattr(sys.modules[exam.__name__],test)    
        aud.stage(test_type,
                  min_time=args['s'], min_hosts=args['N'],
                  waynesses=args['waynesses'], aggregate=args['a'],
                  ignore_status=args['ignore_status'])

        print 'Staging test: '+ test_type.__name__

    # Compute metrics for exams
    aud.run(get_filelist(args['start'],
                         args['end'],
                         pickles_dir = args['dir']))

    # Test metrics for pass/fail.  Print results
    failed_jobs = {}
    for test in args['test']:
        if len(args['t']) > 1: threshold = args['t'][args['test'].index(test)]
        else: threshold = args['t']

        test_type = getattr(sys.modules[exam.__name__],test)    
        aud.test(test_type,threshold)
        failed_jobs[test_type.__name__] = test_report(aud,test_type)

    # Make plots if desired
    if not args['plot']: return failed_jobs
    for test in args['test']:
        if len(args['t']) > 1: threshold = args['t'][args['test'].index(test)]
        else: threshold = args['t']

        test_type = getattr(sys.modules[exam.__name__],test)    
        plotter = plot.MasterPlot(header='Failed test: '+ test_type.__name__,
                                  prefix=test_type.__name__,outdir=args['o'],
                                  processes=args['p'],threshold=threshold,
                                  wide=args['wide'],save=True)
        plotter.run(failed_jobs[test_type.__name__])
    return failed_jobs

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run tests for jobs')
    parser.add_argument('start', help='Start date',
                        type=str,default='')
    parser.add_argument('end', help='End date',
                        type=str,default='')
    parser.add_argument('-test', type=str, nargs='+', 
                        help='Tests to run')
    parser.add_argument('-p', nargs='?', type=int, default=1,
                        help='Set number of processes')
    parser.add_argument('-dir', help='Pickles Directory',
                        type=str, default=cfg.pickles_dir)
    parser.add_argument('-N', help='Set minimum number of hosts',
                        type=int, default=1)
    parser.add_argument('-s', help='Set minimum time in seconds',
                        type=int, default=3600)
    parser.add_argument('-t', help='Set test threshold',
                        type=float, nargs='*',default=[1.0])
    parser.add_argument('-ignore_status', help='Status types to ignore',
                        nargs='*', type=str, default=[])
    parser.add_argument('-waynesses', help='Wayness required',
                        nargs='*', type=int, default=[x+1 for x in range(32)])
    parser.add_argument('-a', help='Aggregate over node', default=True)
    parser.add_argument('-o', help='Output directory',
                        type=str, default='.', metavar='output_dir')
    parser.add_argument('-wide', help='Set wide plot format',
                        action="store_true")
    parser.add_argument('-plot', help='Generate a plot',
                        action="store_true")

    main(**vars(parser.parse_args()))
