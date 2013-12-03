#!/usr/bin/env python
import analyze_conf
import sys
import datetime, glob, job_stats, os, subprocess, time
import operator
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
import tspl, tspl_utils, lariat_utils
import math
import itertools

def getlimits(vals):
    ymin=0.
    ymax=0.
    ymin=min(ymin,min(vals))
    ymax=max(ymin,max(vals))
    return (ymin,ymax)


def main():

  parser = argparse.ArgumentParser(description='Look for high meta data rate'\
                                   ' to Lustre')
  parser.add_argument('-t', metavar='thresh',
                      help='Treshold metadata rate',
                      nargs=1, default=[100000.])
  parser.add_argument('filearg', help='File, directory, or quoted'
                      ' glob pattern', nargs='?',default='jobs')

  n=parser.parse_args()
  thresh=float(n.t[0])
  print thresh


  filelist=tspl_utils.getfilelist(n.filearg)

#  k1=['llite', 'llite', 'llite', 'llite', 'llite',
#      'llite', 'llite', 'llite', 'llite', 'llite',
#      'llite', 'llite', 'llite', 'llite', 'llite',
#      'llite', 'llite', 'llite', 'llite', 'llite',
#      'llite', 'llite', 'llite', 'llite', 'llite',
#      'llite']
#  k2=['open','close','mmap','seek','fsync','setattr',
#      'truncate','flock','getattr','statfs','alloc_inode',
#      'setxattr','getxattr',' listxattr',
#      'removexattr', 'inode_permission', 'readdir',
#      'create','lookup','link','unlink','symlink','mkdir',
#      'rmdir','mknod','rename',]
  k1=['llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', 'llite', 'llite',
      'llite', 'llite', 'llite', ]
  k2=['open','close','mmap','fsync','setattr',
      'truncate','flock','getattr','statfs','alloc_inode',
      'setxattr',' listxattr',
      'removexattr', 'readdir',
      'create','lookup','link','unlink','symlink','mkdir',
      'rmdir','mknod','rename',]

  for file in filelist:
    try:
      ts=tspl.TSPLSum(file,k1,k2)
            
    except tspl.TSPLException as e:
      continue

    if not tspl_utils.checkjob(ts,3600.,range(1,33)):
      continue

    tmid=(ts.t[:-1]+ts.t[1:])/2.0

    ld=lariat_utils.LariatData(ts.j.id,ts.j.end_time,'lariatData')
    
    meta_rate = numpy.zeros_like(tmid)

    for k in ts.j.hosts.keys():
      meta_rate +=numpy.diff(ts.assemble(range(0,len(k1)),k,0))/numpy.diff(ts.t)
      
    meta_rate  /= float(ts.numhosts)

    if numpy.max(meta_rate) > thresh:
      title=ts.title
      if ld.exc != 'unknown':
        title += ', E: ' + ld.exc.split('/')[-1]

      fig,ax=plt.subplots(1,1,figsize=(10,8),dpi=80)
      plt.subplots_adjust(hspace=0.35)
      plt.suptitle(title)

      markers = ('o','x','+','^','s','8','p',
                 'h','*','D','<','>','v','d','.')
          
      colors  = ('b','g','r','c','m','k','y')

      cnt=0
      for v in ts.data:
        for host in v:
          for vals in v[host]:
            rate=numpy.diff(vals)/numpy.diff(ts.t)
            c=colors[cnt % len(colors)]
            m=markers[cnt % len(markers)]
#            print cnt,(cnt % len(colors)), (cnt % len(markers)), k2[cnt], c, m
            
            ax.plot(tmid/3600., rate, marker=m,
                    markeredgecolor=c, linestyle='-', color=c,
                    markerfacecolor='None', label=k2[cnt])
            ax.hold=True
        cnt=cnt+1

      ax.set_ylabel('Meta Data Rate (op/s)')
      tspl_utils.adjust_yaxis_range(ax,0.1)

      handles,labels=ax.get_legend_handles_labels()
      new_handles={}
      for h,l in zip(handles,labels):
        new_handles[l]=h

      box = ax.get_position()
      ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
      ax.legend(new_handles.values(),new_handles.keys(),prop={'size':8},
                bbox_to_anchor=(1.05,1), borderaxespad=0., loc=2)

      fname='_'.join(['metadata',ts.j.id,ts.owner])

      fig.savefig(fname)
      plt.close()



if __name__ == '__main__':
  main()
  
