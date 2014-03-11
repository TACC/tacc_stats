#!/usr/bin/env python
import argparse,sys

from gen import tspl_utils
from exam import tests
from plot import plots
  
def main():

  parser = argparse.ArgumentParser(description='Plot important stats for jobs')
  parser.add_argument('files', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-m', help='Plot mode: lines, hist, percentile',
                      nargs=1, type=str, default=['lines'],
                      metavar='mode')
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-s', help='Set minimum time in seconds',
                      nargs=1, type=int, default=[3600])
  parser.add_argument('-w', help='Set wide plot format', 
                      action='store_true')
  parser.add_argument('-t', help='Treshold Bandwidth', 
                      nargs=1, type=float, default=[0.5], 
                      metavar='threshold')

  args=parser.parse_args()
  filelist=tspl_utils.getfilelist(args.files)

  thresh = args.t[0]
  outdir = args.o[0]

  # Node Imbalance
  print '-----------------'
  print "Imbalance test"
  imb_test = tests.Imbalance(['intel_snb'],['LOAD_L1D_ALL'],
                             processes=args.p[0],threshold=1.0,
                             plot=False)
  imb_test.run(filelist)
  imb_test.find_top_users()
  failed_jobs = imb_test.failed()

  print "Jobs with imbalances"
  print failed_jobs

  imb_test = tests.Imbalance(['intel_snb'],['LOAD_L1D_ALL'],
                             processes=args.p[0],threshold=1.0,
                             plot=True)
  imb_test.run(failed_jobs)
  
  # Idle
  print '-----------------'
  print "Idle host test"
  idle_test = tests.Idle(processes=args.p[0],threshold=1-0.001)
  idle_test.run(filelist)

  print 'Failed Jobs List'
  print idle_test.failed()

  # Catastrophic
  print '-----------------'
  print "Catastrophic test"
  cat_test = tests.Catastrophe(processes=args.p[0],plot=False,threshold=0.001)
  cat_test.run(filelist)
  failed_jobs = cat_test.failed()

  print 'Failed Jobs List'
  print failed_jobs

  cat_test = tests.Catastrophe(processes=args.p[0],plot=True,threshold=0.001)
  cat_test.run(failed_jobs)


  # Low FLOPS test
  print '-----------------'
  print "Low FLOPS test"
  flops_test = tests.LowFLOPS(processes=args.p[0],plot=False,threshold=0.001)
  flops_test.run(filelist)

  print 'Failed Jobs List'
  print flops_test.failed()

  flops_test = tests.LowFLOPS(processes=args.p[0],plot=True,threshold=0.001)
  flops_test.run(failed_jobs)

if __name__ == '__main__':
  main()
  
