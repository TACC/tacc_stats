#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import itertools, argparse, functools, multiprocessing
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')

import matplotlib.pyplot as plt
import numpy
import math
import tspl, tspl_utils, masterplot

def compute_fit_params(ts,ind):

  fit=[]
  for v in ts:
    rate=numpy.divide(numpy.diff(v),numpy.diff(ts.t))
    tmid=(ts.t[:-1]+ts.t[1:])/2.0
    r1=range(ind)
    r2=[x + ind for x in range(len(rate)-ind)]
    a=numpy.trapz(rate[r1],tmid[r1])/(tmid[ind]-tmid[0])
    b=numpy.trapz(rate[r2],tmid[r2])/(tmid[-1]-tmid[ind])
    fit.append((a,b))

  return fit
    
                      

def fit_step(fn,k1,k2,genplot=False,res={}):
  
  try:
    ts=tspl.TSPLSum(fn,k1,k2)
  except tspl.TSPLException as e:
    return
  
  ignore_qs=['gpu','gpudev','vis','visdev']
  if not tspl_utils.checkjob(ts,3600,range(1,33),ignore_qs):
    return
  elif ts.numhosts < 2: # At least 2 hosts
    print ts.j.id + ': 1 host'

  bad_hosts=tspl_utils.lost_data(ts)
  if len(bad_hosts) > 0:
    print ts.j.id, ': Detected hosts with bad data: ', bad_hosts
    return
    
  vals=[]
  for i in [x + 2 for x in range(ts.size-4)]:
    vals.append(compute_fit_params(ts,i))

  vals2=[]
  for v in vals:
    vals2.append([ b/a for (a,b) in v])

  arr=numpy.array(vals2)
  brr=numpy.transpose(arr)

  (m,n)=numpy.shape(brr)

  if genplot:
    fig,ax=plt.subplots(1,1,dpi=80)
    ax.hold=True
    for i in range(m):
      ax.semilogy(brr[i,:])
    fig.savefig('foo.pdf')
    plt.close()

  r=[]
  for i in range(m):
    jnd=numpy.argmin(brr[i,:])
    r.append((jnd,brr[i,jnd]))

  res[fn]=r


def main():
  parser = argparse.ArgumentParser(description='')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()
  
  filelist=tspl_utils.getfilelist(n.filearg)

  # Hash value must be a list
  k1={'amd64' : ['amd64_sock'],
      'intel_snb': ['intel_snb']}
  k2={'amd64' : ['DRAM'],
      'intel_snb': ['LOAD_L1D_ALL']}

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  res    = m.dict()                                         

  fit_partial=functools.partial(fit_step,k1=k1,k2=k2,genplot=False,res=res)

  if len(filelist) != 0:
    pool.map(fit_partial,filelist)
    pool.close()
    pool.join()

  for fn in res.keys():
    for (ind,ratio) in res[fn]:
      if ratio < 1e-3:
        print fn + ': ' + str(res[fn])
        masterplot.mp_wrapper(fn,'lines',False,n.o[0],'step',
                              1,[x+1 for x in range(16)],
                              header='Step Function Performance',wide=True) 
        break
   
if __name__ == '__main__':
  main()
