#!/usr/bin/env python
import argparse,sys

import analyze_conf
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
  print "Imbalance test"
  imb_test = tests.Imbalance(['intel_snb'],['INSTRUCTIONS_RETIRED'],
                             processes=2,aggregated=False,plot=True)
  imb_test.run(filelist,threshold=0.25)

  # Idle
  print "Idle host test"
  idle_test = tests.Idle(processes=2)
  idle_test.run(filelist,threshold=1-0.001)
  print "Jobs with idle hosts"
  print idle_test.failed()

  # Catastrophic
  print "Catastrophic test"
  cat_test = tests.Catastrophe(processes=2,plot=True)
  cat_test.run(filelist,threshold=0.001)
  jobs = cat_test.failed()

  # Low FLOPS test
  print "Low FLOPS test"
  flops_test = tests.Low_FLOPS(processes=2,plot=True)
  flops_test.run(filelist,threshold=0.001)
  jobs = flops_test.failed()

  """
  # Membw
  print "Memory Bandwidth test"
  membw_test = tests.Mem_bw(processes=2)
  membw_test.run(filelist,threshold=thresh)
  jobs = membw_test.failed()

  plot=plots.MasterPlot(processes=2)
  plot.run(jobs,mode='lines',threshold=thresh,
           outdir=outdir,save=True,prefix='highmembw',
           header='High Memory Bandwidth',)

  # MemUsage Plot
  print "MemUsage Plot"
  plot = plots.MemUsage(processes=2)
  plot.run(idle_test.failed())
  """

if __name__ == '__main__':
  main()
  
