#!/usr/bin/python

import cPickle as pickle
import datetime
import glob
import job_stats
import math
import numpy
import os
import pymongo
import scipy
import subprocess
import sys
import tarfile
import time
import json
from scipy import stats
import gzip
import getProcdumpData
import traceback

#ignore warnings from numpy
numpy.seterr(all='ignore')

#LARIAT_DATA_PATH = '/data/scratch/Lonestar/lariatData'
LARIAT_DATA_PATH = sys.argv[2]

def calculate_stats(v):
  res = {
    'avg': 0.0,
    'cov': 0.0,
    'kurt': 0.0,
    'max': 0.0,
    'median': 0.0,
    'min': 0.0,
    'skew': 0.0,
    }

  if v:

    (
      v_n,
      (v_min, v_max),
      v_avg,
      v_var,
      v_skew,
      v_kurt,
      ) = scipy.stats.describe(v)

    res['max'] = v_max
    if 0 < v_max:
      res['avg'] = v_avg
      res['kurt'] = v_kurt
      res['median'] = numpy.median(v, axis=0) + 0.0
      res['min'] = v_min + 0.0
      res['skew'] = v_skew
      res['max'] += 0.0
      if 0 < v_avg:
        res['cov'] = math.sqrt(v_var) / v_avg
  return res


def main():
  
  summaryDict = {}

  path = sys.argv[1]
  listing = os.listdir(path)
  os.chdir(path)

  j = None
  metrics = None
  
  for infile in listing:
    
    f = open(infile, 'r')
    j = pickle.load(f)
    sys.stderr.write( '\nID: '+str(j.acct['id'])+' \n' )
    db_key = {'Jobid': j.acct['id']}

    walltime = max(j.end_time - j.start_time, 0)
    
    #summaryDict['Jobid'] = j.acct['id']
    #summaryDict['picklefile'] = path + '/' + infile
    #summaryDict['walltime'] = walltime
    
    #for i in ['granted_pe', 'queue', 'exit_status', 'account', 'owner']:
    #  if i in j.acct.keys():
    #    summaryDict[i] = j.acct[i]

    if j.hosts.keys():
      #summaryDict['nHosts'] = len(j.hosts)
      pass
    else:
      summaryDict['nHosts'] = 0
      continue

    if 0 == walltime:
      continue

    #metrics = {
    #  'intel_pmc3': ['PMC2'], # FP_COMP_OPS_EXE_SSE (U2), FP_COMP_OPS_EXE_X87 (Lonestar, Stampede) - FLOPS
    #  'block': ['rd_ios', 'rd_sectors', 'wr_ios', 'wr_sectors'],
    #  'cpu': ['system', 'user', 'idle', 'all'],
    #  'ib_ext': ['port_rcv_pkts', 'port_rcv_data', 'port_xmit_pkts', 'port_xmit_data'],
    #  'panfs': ['op__read__total_bytes', 'op__write__total_bytes', 'op__getattr_total', 'op__setattr', 'op__write_retried'],
    #  'nfs': ['normal_read', 'normal_write', 'direct_read', 'direct_write', 'server_read', 'server_write', 'rpc_getattr_op', 'rpc_setattr_op'],
    #  'mem': ['MemUsed', 'FilePages', 'Slab'],
    #  'net': ['rx_packets', 'rx_bytes', 'tx_packets', 'tx_bytes']
    #  }
    # WE WANT TO USE ALL THE METRICS IN THE TACC_STATS FILE
    metrics = {}
    for t in j.schemas.keys():
      metrics[t] = []
      if t == 'cpu':
        metrics[t].append('all')
      for m in j.schemas[t]:
        metrics[t].append(m)

    indices = {}
    sums = {}
    series = {}  # we keep the time series data here, because we need to calculate min/max/median & 1/2/3/4th order of moments

    for k in metrics.keys():
      indices[k] = {}
      sums[k] = {}
      series[k] = {}
      for l in metrics[k]:
        try:
          if l in j.get_schema(k):
            indices[k][l] = j.get_schema(k)[l].index
        except:
          sys.stderr.write( 'ERROR: summary metric ' + str(l) + ' not in the schema\n' )
          sys.stderr.write( 'ERROR: %s\n' % sys.exc_info()[0] )
          sys.stderr.write( '%s\n' % traceback.format_exc() )
        sums[k][l] = {}
        series[k][l] = {}

    reciprocals = []

    # get the reciprocals of intervals (of timestamps)
    # so we can calculate "rates" later

    for n in range(1, len(j.times)):
      delta = j.times[n] - j.times[n - 1]
      if 0 < delta:
        reciprocals.append(1.0 / delta)
      else:
        reciprocals.append(0)

    nCores_allhosts = 0
    nHosts = 0
    nIntervals = len(j.times) - 1
    if 0 >= nIntervals:
      continue

    for i in j.hosts.keys():  # for all the hosts present in the file
      nHosts += 1
      nCoresPerSocket = 1

      if 'cpu' in j.hosts[i].stats.keys() and 'mem' \
        in j.hosts[i].stats.keys():
        nCoresPerSocket = len(j.hosts[i].stats['cpu']) \
          // len(j.hosts[i].stats['mem'])

      for k in indices.keys():
        if k in j.hosts[i].stats.keys():
          for interface in j.hosts[i].stats[k].keys():
            if k == 'cpu':  # special handling for 'cpu'
              nCores_allhosts = nCores_allhosts + 1
              if interface not in sums['cpu']['all'].keys():
                sums['cpu']['all'][interface] = 0
                series['cpu']['all'][interface] = []
              sums['cpu']['all'][interface] = sums['cpu']['all'][interface] \
                + sum(j.hosts[i].stats['cpu'][interface][nIntervals]) \
                / walltime
              v = []
              for n in range(nIntervals + 1):
                v.append(sum(j.hosts[i].stats['cpu'][interface][n]))
              rates = [(v[n] - v[n - 1]) * reciprocals[n - 1] for n in
                       range(1, len(v))]
              series['cpu']['all'][interface].extend(rates)

            for l in indices[k].keys():
              v = j.hosts[i].stats[k][interface][:, indices[k][l]]
              if interface not in sums[k][l].keys():
                sums[k][l][interface] = 0
                series[k][l][interface] = []
              if k != 'mem':
                sums[k][l][interface] = sums[k][l][interface] + (v[-1]
                      - v[0]) / walltime  # divide walltime here, to avoid overflow in summation
                if len(reciprocals) == len(v) - 1:
                  rates = [(v[n] - v[n - 1]) * reciprocals[n - 1] for n in
                           range(1, len(v))]
                  series[k][l][interface].extend(rates)
              else:
                if 2 < len(v):

                 # for memory metrics, throw away the first (and the last, if possible) results
                 # since they are measured at the endpoints of a job

                  v = v[1:len(v) - 1]
                else:
                  v = v[1:len(v)]
                series[k][l][interface].extend(v / nCoresPerSocket)

    if 0 < nCores_allhosts:

    # SSE_FLOPS

      s = 0
      v = []
      if 'intel_pmc3' in sums.keys():
        for l in sums['intel_pmc3']['PMC2'].keys():

          # iterate all CPU cores

          s += sums['intel_pmc3']['PMC2'][l]
          v.extend(series['intel_pmc3']['PMC2'][l])
      if v:
        v = calculate_stats(v)
        if 0 < v['max']:
          v['overall_avg'] = s / nCores_allhosts
          summaryDict['SSE_FLOPS'] = v

    # memory usage

      v = []
      v2 = []
      v3 = []
      for l in sums['mem']['MemUsed'].keys():

        # iterate all memory sockets

        v.extend(series['mem']['MemUsed'][l])
        v2.extend(series['mem']['FilePages'][l])
        v3.extend(series['mem']['Slab'][l])
      if v:
        res = calculate_stats(v)
        if 0 < res['max']:
          summaryDict['mem.used'] = res
        res = calculate_stats([a - b - c for (a, b, c) in zip(v, v2, v3)])
        if 0 < res['max']:
          summaryDict['mem.used_minus_diskcache'] = res

    # cpu usage

      s = 0
      v = []
      for l in sums['cpu']['all'].keys():

        # iterate all CPU cores

        s += sums['cpu']['all'][l]
        v.extend(series['cpu']['all'][l])
      if 0 < s:
        for l in indices['cpu'].keys():
          s2 = 0
          v2 = []
          for k in sums['cpu'][l].keys():
            s2 += sums['cpu'][l][k]
            v2.extend(series['cpu'][l][k])

          v2 = calculate_stats([a / b for (a, b) in zip(v2, v)])
          if 0 < v2['max']:
            v2['overall_avg'] = s2 / s
            summaryDict['cpu.'+l] = v2

    del sums['cpu']  # we are done with 'cpu'
    del sums['mem']  # we are done with 'mem'
    if 'intel_pmc3' in sums.keys():
      del sums['intel_pmc3']  # we are done with 'amd64_core'

  # deal with general cases

    for l in sums.keys():
      for k in sums[l].keys():
        for i in sums[l][k].keys():
          v = calculate_stats(series[l][k][i])
          #if 0 < v['max']:
          v['overall_avg'] = sums[l][k][i] / nHosts
          summaryDict[l + '.' + i + '.' + k] = v
  
  # add in lariat data
  endTimestamp = j.acct['end_time']
  endDateObj = datetime.datetime.fromtimestamp(endTimestamp)
  lariatDataDatePath = os.path.join(LARIAT_DATA_PATH, endDateObj.strftime('%Y'), endDateObj.strftime('%m'), endDateObj.strftime('lariatData-sgeT-%Y-%m-%d.json'))
  try:
    if os.path.isfile(lariatDataDatePath):
      lariatDataFile = open(lariatDataDatePath, 'r')
      lariatJson = json.load(lariatDataFile)
      for k in lariatJson.keys():
        if str(j.acct['id']) == str(k):
          summaryDict['lariat'] = lariatJson[k][0]
          continue
      lariatDataFile.close()
  except:
    sys.stderr.write( 'ERROR CAUGHT: %s\n' % sys.exc_info()[0] )
    sys.stderr.write( 'ERROR CAUGHT: lariat data will not be in summary\n')
    sys.stderr.write( '%s\n' % traceback.format_exc() )
    summaryDict['Error'] = "Lariat data not found"

  #add hosts
  summaryDict['hosts'] = []
  for i in j.hosts.keys():
    summaryDict['hosts'].append(i)
  
  #add account data
  summaryDict['acct'] = j.acct

  # add schema outline
  summaryDict['schema'] = {}
  try:
    for k in metrics:
      for l in metrics[k]:
        if l in j.get_schema(k):
          if k not in summaryDict['schema']:
            summaryDict['schema'][k]={}
          summaryDict['schema'][k][l] = str( j.get_schema(k)[l] )
  except:
    if (summaryDict['nHosts'] != 0):
      sys.stderr.write( 'ERROR: %s\n' % sys.exc_info()[0] )
      sys.stderr.write( '%s\n' % traceback.format_exc() )
      summaryDict['Error'] = "schema data not found"

  #get exe files running
  startDateObj = datetime.datetime.fromtimestamp(j.acct['start_time'])
  taccStatsFile = "/data/scratch/Rush/archive/" + str(j.acct['hostname']) + "/" + startDateObj.strftime('%Y%m%d') + ".gz"

  try:
    procDumpData = getProcdumpData.getProcdumpData( taccStatsFile, str(j.acct['id']) )

    #sys.stderr.write(str(jobid))
    #sys.stderr.write(cmd)
    #procDumpData = subprocess.check_output(cmd, shell=True).split('\n')[:-1]
    summaryDict['procDump'] = str(procDumpData)
  except Exception, e:
    sys.stderr.write( 'ERROR in procDumpData: %s\n' % e )
    sys.stderr.write( '%s\n' % traceback.format_exc() )

  #print out json to stdout
  print json.dumps(summaryDict, indent=2)

if __name__ == '__main__':
  main()

