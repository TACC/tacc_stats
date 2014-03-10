#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import matplotlib
# Set the matplotlib output mode from config if it exists
if not 'matplotlib.pyplot' in sys.modules:
  try:
    matplotlib.use(analyze_conf.matplotlib_output_mode)
  except NameError:
    matplotlib.use('pdf')
    
import matplotlib.pyplot as plt
import numpy
import scipy, scipy.stats
import argparse
import re
import multiprocessing
import functools
import tspl, tspl_utils, masterplot

def getuser(file,user):
  try:
    k1=['intel_snb_imc', 'intel_snb_imc', 'intel_snb', 
        'lnet', 'lnet', 'ib_sw','ib_sw','cpu',
        'intel_snb', 'intel_snb', 'mem']
    k2=['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
        'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user',
        'SSE_D_ALL', 'SIMD_D_256', 'MemUsed']

    try:
      ts=tspl.TSPLSum(file,k1,k2)
    except tspl.TSPLException as e:
      return

    if ts.owner != user:
      return
    
    ignore_qs=['gpu','gpudev','vis','visdev']
    if not tspl_utils.checkjob(ts,1.,range(1,33),ignore_qs):
      return

    tmid=(ts.t[:-1]+ts.t[1:])/2.0
    dt=numpy.diff(ts.t)

    dram_rate  = numpy.zeros_like(tmid)
    l1_rate    = numpy.zeros_like(tmid)
    lnet_rate  = numpy.zeros_like(tmid)
    ib_rate    = numpy.zeros_like(tmid)
    user_rate  = numpy.zeros_like(tmid)
    flops_rate = numpy.zeros_like(tmid)
    mem_usage  = numpy.zeros_like(tmid)

    for host in ts.j.hosts.keys():
      dram_rate  += numpy.diff(ts.assemble([0,1],host,0))/dt
      l1_rate    += numpy.diff(ts.assemble([2],host,0))/dt
      lnet_rate  += numpy.diff(ts.assemble([3,4],host,0))/dt
      ib_rate    += numpy.diff(ts.assemble([5,6,-3,-4],host,0))/dt
      user_rate  += numpy.diff(ts.assemble([7],host,0))/dt
      flops_rate += numpy.diff(ts.assemble([8,9],host,0))/dt
      v           = ts.assemble([10],host,0)
      mem_usage  += (v[:-1]+v[1:])/2.0
      

    dram_rate  /= float(ts.numhosts)*1024.*1024.*1024./64.
    l1_rate    /= float(ts.numhosts)*1024.*1024./64.
    lnet_rate  /= float(ts.numhosts)*1e6
    ib_rate    /= float(ts.numhosts)*1e6
    user_rate  /= float(ts.numhosts)*100.*ts.wayness
    flops_rate /= float(ts.numhosts)*1e9
    mem_usage  /= float(ts.numhosts)*(1024.*1024.*1024.)

    min_dram_rate   = numpy.min(dram_rate)
    max_dram_rate   = numpy.max(dram_rate)
    mean_dram_rate  = numpy.mean(dram_rate)
    min_l1_rate     = numpy.min(l1_rate)
    max_l1_rate     = numpy.max(l1_rate)
    mean_l1_rate    = numpy.mean(l1_rate)
    min_lnet_rate   = numpy.min(lnet_rate)
    max_lnet_rate   = numpy.max(lnet_rate)
    mean_lnet_rate  = numpy.mean(lnet_rate)
    min_ib_rate     = numpy.min(ib_rate)
    max_ib_rate     = numpy.max(ib_rate)
    mean_ib_rate    = numpy.mean(ib_rate)
    min_user_rate   = numpy.min(user_rate)
    max_user_rate   = numpy.max(user_rate)
    mean_user_rate  = numpy.mean(user_rate)
    min_flops_rate  = numpy.min(flops_rate)
    max_flops_rate  = numpy.max(flops_rate)
    mean_flops_rate = numpy.mean(flops_rate)
    min_mem_usage   = numpy.min(mem_usage)
    max_mem_usage   = numpy.max(mem_usage)
    mean_mem_usage  = numpy.mean(mem_usage)
    

    return (ts.j.acct['end_time'],
            min_dram_rate,max_dram_rate,mean_dram_rate,
            min_l1_rate,max_l1_rate,mean_l1_rate,
            min_lnet_rate,max_lnet_rate,mean_lnet_rate,
            min_ib_rate,max_ib_rate,mean_ib_rate,
            min_user_rate,max_user_rate,mean_user_rate,
            min_flops_rate,max_flops_rate,mean_flops_rate,
            min_mem_usage,max_mem_usage,mean_mem_usage,
            ts.j.id)
  except Exception as e:
    import sys
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    raise e


def main():
  parser=argparse.ArgumentParser(description='Deal with a directory of pickle'
                                 ' files nightly')
  parser.add_argument('-p', help='Set number of processes',
                      nargs=1, type=int, default=[1])
  parser.add_argument('-o', help='Output directory',
                      nargs=1, type=str, default=['.'], metavar='output_dir')
  parser.add_argument('-u', help='User',
                      nargs=1, type=str, default=['bbarth'], metavar='username')
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')
  n=parser.parse_args()

  filelist=tspl_utils.getfilelist(n.filearg)
  target_user=n.u[0]

  pool   = multiprocessing.Pool(processes=n.p[0])
  m      = multiprocessing.Manager()
  files  = m.list()


  partial_getuser=functools.partial(getuser,user=target_user)
  res = pool.map(partial_getuser,filelist)
  pool.close()
  pool.join()

  res  = filter(lambda x: x != None, res)
  if len(res) == 0:
    print 'no jobs found'
    return

  res_sorted = sorted(res, key=lambda x:x[0])
  res2 = zip(*res_sorted)


  t=res2[0]
  min_dram_rate=res2[1]
  max_dram_rate=res2[2]
  mean_dram_rate=res2[3]
  min_l1_rate=res2[4]
  max_l1_rate=res2[5]
  mean_l1_rate=res2[6]
  min_lnet_rate=res2[7]
  max_lnet_rate=res2[8]
  mean_lnet_rate=res2[9]
  min_ib_rate=res2[10]
  max_ib_rate=res2[11]
  mean_ib_rate=res2[12]
  min_user_rate=res2[13]
  max_user_rate=res2[14]
  mean_user_rate=res2[15]
  min_flops_rate=res2[16]
  max_flops_rate=res2[17]
  mean_flops_rate=res2[18]
  min_mem_usage=res2[19]
  max_mem_usage=res2[20]
  mean_mem_usage=res2[21]
  ids=res2[22]

  start_date = datetime.datetime.fromtimestamp(t[0]).strftime('%Y-%m-%d %H:%M:%S')
  end_date   = datetime.datetime.fromtimestamp(t[-1]).strftime('%Y-%m-%d %H:%M:%S')

  fig,ax=plt.subplots(6,1,figsize=(8,12),dpi=80)
  plt.subplots_adjust(hspace=0.35)

  ax[0].plot(t,min_flops_rate,'x',t,mean_flops_rate,'+',t,max_flops_rate,'*')
  ax[0].set_ylabel('GFlops/s')
  ax[0].set_xticklabels(labels=[])
  
  ax[1].plot(t,min_dram_rate,'x',t,mean_dram_rate,'+',t,max_dram_rate,'*')
  ax[1].set_ylabel('DRAM BW MB/s')
  ax[1].set_xticklabels(labels=[])
  
  ax[2].plot(t,min_mem_usage,'x',t,mean_mem_usage,'+',t,max_mem_usage,'*')
  ax[2].set_ylabel('DRAM Usage GB')
  ax[2].set_xticklabels(labels=[])
  
  ax[3].plot(t,min_lnet_rate,'x',t,mean_lnet_rate,'+',t,max_lnet_rate,'*')
  ax[3].set_ylabel('Lnet Rate MB/s')
  ax[3].set_xticklabels(labels=[])
  
  ax[4].plot(t,min_ib_rate,'x',t,mean_ib_rate,'+',t,max_ib_rate,'*')
  ax[4].set_ylabel('IB - Lnet Rate MB/s')
  ax[4].set_xticklabels(labels=[])
  
  ax[5].plot(t,min_user_rate,'x',t,mean_user_rate,'+',t,max_user_rate,'*')
  ax[5].set_ylabel('CPU User Fraction')
  ax[5].set_xticklabels(labels=[])

  for i in range(6):
    tspl_utils.adjust_yaxis_range(ax[i],0.1)

  ax[5].set_xlabel('t')

  plt.suptitle(target_user+' '+start_date+' -- '+end_date)
  fname=target_user
  fig.savefig(fname)
  plt.close()

  print 'Found', len(res_sorted), 'jobs for', target_user, ids

if __name__ == "__main__":
  main()
