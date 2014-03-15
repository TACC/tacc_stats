#!/usr/bin/env python
import argparse,sys
sys.path.append('../lib')
from sys_conf import lariat_path
from analysis.gen  import tspl_utils
from analysis.exam import tests
from analysis.plot import plots
  
def main():

  parser = argparse.ArgumentParser(description='Plot important stats for jobs')
  parser.add_argument('files', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-s', help='Set minimum time in seconds',
                      nargs=1, type=int, default=[3600])
  parser.add_argument('-w', help='Set wide plot format',default=True)

  args=parser.parse_args()
  filelist=tspl_utils.getfilelist(args.files)

  plotter = plots.MasterPlot(outdir=args.o[0],processes=args.p[0],                             
                             wide=args.w,save=True)


  ### Node Imbalance
  print '-----------------'
  print "Imbalance test"
  imb_test = tests.Imbalance(['intel_snb'],['LOAD_L1D_ALL'],
                             processes=args.p[0],
                             threshold=1.0,
                             aggregate=True)
  imb_test.run(filelist)
  imb_test.find_top_users()
  print "Jobs with imbalances"
  print imb_test.failed()

  plotter.threshold=imb_test.threshold
  plotter.prefix='imbalance'
  plotter.header='Potentially Imbalanced'
  for f in imb_test.failed():
    plotter.plot(f)

  plotter.mode='percentile'
  plotter.header='Potentially Imbalanced (%)'
  for f in imb_test.failed():
    plotter.plot(f)
  
  ### Idle Test
  print '-----------------'
  print "Idle host test"
  idle_test = tests.Idle(processes=args.p[0],threshold=1-0.001)
  idle_test.run(filelist)
  print 'Failed Jobs List'
  print idle_test.failed()

  ### Catastrophic Test
  print '-----------------'
  print "Catastrophic test"
  cat_test = tests.Catastrophe(processes=args.p[0],threshold=0.001,
                               min_hosts=2)
  cat_test.run(filelist)
  print 'Failed Jobs List'
  print cat_test.failed()

  plotter.mode='lines'
  plotter.prefix='step'
  plotter.threshold=cat_test.threshold
  plotter.header='Step Function Performance'
  for f in cat_test.failed():
    plotter.plot(f)

  ### Low FLOPS Test
  print '-----------------'
  print "Low FLOPS test"
  flops_test = tests.LowFLOPS(processes=args.p[0],threshold=0.001)
  flops_test.run(filelist)
  print 'Failed Jobs List'
  print flops_test.failed()

  plotter.mode='lines'
  plotter.prefix='lowflops'
  plotter.header='Measured Low Flops'
  plotter.threshold=flops_test.threshold
  for f in flops_test.failed():
    plotter.plot(f)

  plotter.mode='percentile'
  plotter.header='Measured Low Flops (%)'
  for f in flops_test.failed():
    plotter.plot(f)

if __name__ == '__main__':
  main()
  
