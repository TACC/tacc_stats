#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('pdf')
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

def plot_correlation(ts,r,full,output_dir='.'):
  tmid=(ts.t[:-1]+ts.t[1:])/2.0
  fig, ax=plt.subplots(2,2,figsize=(10, 10), dpi=80)
  ax[0][0].hold=True
  ax[0][1].hold=True
  ax[1][0].hold=True
  ax[1][1].clear()

  mx=0.
  my=0.

  for k in ts.data[0].keys():
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

  xmin,xmax=tspl_utils.expand_range(0.,mx,.1)
  ymin,ymax=tspl_utils.expand_range(0.,my,.1)
  tmin,tmax=tspl_utils.expand_range(0.,tmid[-1]/3600,.1)
  ax[0][0].set_xlim(left=xmin,right=xmax)
  ax[0][0].set_ylim(bottom=ymin,top=ymax)
  ax[1][0].set_xlim(left=xmin,right=xmax)
  ax[1][0].set_ylim(bottom=tmax,top=tmin)
  ax[0][1].set_ylim(bottom=ymin,top=ymax)
  ax[0][1].set_xlim(left=tmin,right=tmax)
  try:
    fname='_'.join(['graph',ts.j.id,ts.j.acct['owner'],
                    ts.k1[0],ts.k2[0],'vs',
                    ts.k1[1],ts.k2[1]])+full
  except:
    fname='_'.join(['graph',ts.j.id,
                    ts.k1[0],ts.k2[0],'vs',
                    ts.k1[1],ts.k2[1]])+full


  fig.savefig(output_dir+'/'+fname)
  plt.close()


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
      plot_correlation(ts,r,full)
      
if __name__ == "__main__":
  main()
