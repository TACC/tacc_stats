#!/usr/bin/env python
import sys
sys.path.append('../../monitor')
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

# Compute Pearson's R of the rates over all hosts in the loaded job
# Return the smallest R for
def pearson(ts):
  p=[]
  for k in ts.data[0].keys():
    for i in range(len(ts.data[0][k])):
      p.append(scipy.stats.
               pearsonr(numpy.diff(ts.data[1][k][i])/numpy.diff(ts.t),
                        numpy.diff(ts.data[0][k][i])/numpy.diff(ts.t))[0])

  return(min(p))

# Compute Pearson's R and plot a graph if the correlation is low
def main():

  parser = argparse.ArgumentParser(description='Look for lack of correlation'
                                   ' between two key pairs/')
  parser.add_argument('threshold', help='Treshold Pearson R',
                      nargs='?', default=0.8)
  parser.add_argument('keya1', help='Key A1', nargs='?',
                      default='amd64_core')
  parser.add_argument('keya2', help='Key A2', nargs='?',
                      default='DCSF')
  parser.add_argument('keyb1', help='Key B1', nargs='?',
                      default='amd64_core')
  parser.add_argument('keyb2', help='Key B2', nargs='?',
                      default='SSE_FLOPS')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  parser.add_argument('-f', help='Set full mode', action='store_true')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)

  threshold=n.threshold
  k1=[n.keya1, n.keyb1]
  k2=[n.keya2, n.keyb2]

  for file in filelist:
    try:
      if n.f:
        full='_full'
        ts=tspl.TSPLBase(file,k1,k2)
      else:
        full=''
        ts=tspl.TSPLSum(file,k1,k2)
    except tspl.TSPLException as e:
      continue

    if not tspl_utils.checkjob(ts,3600,16):
      continue
    
    r=pearson(ts)
    print ts.j.id + ': ' + str(r)
    if abs(r) < float(threshold) :
      print '---------------------'
      tmid=(ts.t[:-1]+ts.t[1:])/2.0
      fig, ax=plt.subplots(2,2,figsize=(10, 10), dpi=80)
      ax[0][0].hold=True
      ax[0][1].hold=True
      ax[1][0].hold=True
      ax[1][1].clear()

      mx=0.
      my=0.

      for k in ts.data[0].keys():
        print len(ts.data[0][k])
        for i in range(len(ts.data[0][k])):
          first_rate=numpy.diff(ts.data[0][k][i])/numpy.diff(ts.t)
          second_rate=numpy.diff(ts.data[1][k][i])/numpy.diff(ts.t)
          mx=max(mx,max(first_rate))
          my=max(my,max(second_rate))
          ax[0][0].plot(first_rate,second_rate,'.')
          ax[1][0].plot(first_rate[::-1],tmid[::-1]/3600.)
          ax[0][1].plot(tmid/3600.,second_rate)

      ax[0][0].set_xlabel('Total ' + ts.label(ts.k1[0],ts.k2[0]) + '/s')
      ax[0][0].set_ylabel('Total ' + ts.label(ts.k1[1],ts.k2[1]) + '/s')
      ax[1][0].set_ylabel('Time (hr)')
      ax[1][0].set_xlabel('Total ' + ts.label(ts.k1[0],ts.k2[0]) + '/s')
      ax[0][1].set_xlabel('Time (hr)')
      ax[0][1].set_ylabel('Total ' + ts.label(ts.k1[1],ts.k2[1]) + '/s')

      plt.subplots_adjust(hspace=.25)
      title=ts.title + ', R=%(R)-8.3g' % { 'R' : r}
      plt.suptitle(title)
      ax[0][0].set_xlim(left=0.,right=1.1*mx)
      ax[0][0].set_ylim(bottom=0.,top=1.1*my)
      ax[1][0].set_xlim(left=0.,right=1.1*mx)
      ax[1][0].set_ylim(bottom=tmid[-1]*1.05/3600.,top=0.)
      ax[0][1].set_ylim(bottom=0.,top=1.1*my)
      fname1='graph_'+ts.j.id+'_'+ts.k1[0]+'_'+ts.k2[0]+ \
             '_vs_'+ts.k1[1]+'_'+ts.k2[1]+full
      fig.savefig(fname1)
      plt.close()

if __name__ == "__main__":
  main()
