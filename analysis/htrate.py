#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
if not 'matplotlib.pyplot' in sys.modules:
  matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import tspl, tspl_utils

class Colors:
  def __init__(self):
    self.colors=['b','g','r','c','m','y','k']
    self.loc=0

  def next(self):
    if self.loc == len(self.colors):
      self.loc=0
    c=self.colors[self.loc]
    self.loc+=1
    return c


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', help='Set full mode', action='store_true')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')

  n=parser.parse_args()
  filelist=tspl_utils.getfilelist(n.filearg)


  for file in filelist:
    try:
      full=''
      ts=tspl.TSPLBase(file,['amd64_sock', 'amd64_sock', 'amd64_sock'],
                      ['HT0', 'HT1', 'HT2'])
    except tspl.TSPLException as e:
      continue
    
    if not tspl_utils.checkjob(ts,3600,16): # 1 hour, 16way only
      continue
    elif ts.numhosts < 2: # At least 2 hosts
      print ts.j.id + ': 1 host'
      continue

    print ts.j.id
    tmid=(ts.t[:-1]+ts.t[1:])/2.0
    dt=numpy.diff(ts.t)

    fig,ax=plt.subplots(1,1,figsize=(8,6),dpi=80)
    ax.hold=True
    xmin,xmax=[0.,0.]
    c=Colors()
    for k in ts.j.hosts.keys():
      h=ts.j.hosts[k]
      col=c.next()
      for i in range(3):
        for j in range(4):
          rate=numpy.divide(numpy.diff(ts.data[i][k][j]),dt)
          xmin,xmax=[min(xmin,min(rate)),max(xmax,max(rate))]
          ax.plot(tmid/3600,rate,'-'+col)
    if xmax > 2.0e9:
      print ts.j.id + ' over limit: %(v)8.3f' % {'v' : xmax}
    else:
      plt.close()
      continue

    plt.suptitle(ts.title)
    xmin,xmax=tspl_utils.expand_range(xmin,xmax,.1)
    ax.set_ylim(bottom=xmin,top=xmax)

    fname='_'.join(['graph',ts.j.id,'HT_rates'])
    fig.savefig(fname)
    plt.close()

if __name__ == '__main__':
  main()
  
