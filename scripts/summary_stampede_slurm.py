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
import traceback
from scipy import stats

#ignore warnings from numpy
numpy.seterr(all='ignore')

class LariatManager:
    def __init__(self, lariatpath):
        self.lariatpath = lariatpath
        self.lariatdata = dict()
        self.filesprocessed = []
        self.errors = dict()

    def find(self, jobid, jobstarttime):

        if jobid in self.lariatdata:
            return self.lariatdata[jobid]

        for days in (0, -1, 1):
            searchday = datetime.datetime.utcfromtimestamp(jobstarttime) + datetime.timedelta(days)
            lfilename = os.path.join(self.lariatpath, searchday.strftime('%Y'), searchday.strftime('%m'), searchday.strftime('lariatData-sgeT-%Y-%m-%d.json'))
            self.loadlariat(lfilename)

            if jobid in self.lariatdata:
                return self.lariatdata[jobid]

        return None

    def loadlariat(self, filename):

        if filename in self.filesprocessed:
            # No need to reparse file. If the job data was in the file, then this search
            # function would not have been called.
            return

        try:
            with open(filename, "rb") as fp:

                # Unfortunately, the lariat data is not in valid json
                # This workaround converts the illegal \' into valid quotes
                content = fp.read().replace("\\'", "'")
                lariatJson = json.loads(content)

                for k,v in lariatJson.iteritems():
                    self.lariatdata[k] = v[0]

                self.filesprocessed.append(filename)

        except Exception as e:
            self.errors[filename] = "Error processing {}. Error was {}.".format(filename, e)


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

    res['max'] = float(v_max)
    res['avg'] = v_avg
    res['kurt'] = v_kurt
    res['median'] = float(numpy.median(v, axis=0))
    res['min'] = float(v_min)
    res['skew'] = v_skew

    if 0 < v_avg:
      res['cov'] = math.sqrt(v_var) / v_avg

  return res


def main():
  
  path = sys.argv[1]

  if len(sys.argv) > 2:
      lariatcache = LariatManager(sys.argv[2])
  else:
      lariatcache = None

  if len(sys.argv) > 3:
    outdir = sys.argv[3]
  else:
    outdir = None

  if os.path.isfile(path):
    listing = [path]
  else:
    listing = [ os.path.join(path, x) for x in os.listdir(path) ]
    
  if outdir:
    # Batch processing mode - each input file gets its own output json file
    for fname in listing:
      if os.path.isfile(fname):
        outfile = os.path.join(outdir, os.path.basename(fname) + ".json")
        summarise([fname], outfile, lariatcache)
  else:
    # Single-shot mode - all input files get process and the combined
    # result goes to stdout
    summarise(listing, "/dev/stdout", lariatcache)

  return

def summarise(listing, outputfilename, lariatcache):
  
  if outputfilename != "/dev/stdout":
    if os.path.exists(outputfilename):
      sys.stderr.write("Output file {} already exists. Skipping\n".format(outputfilename))
      return

  summaryDict = {}
  summaryDict['Error'] = []


  j = None
  metrics = None
  
  for infile in listing:
    
    f = open(infile, 'r')
    j = pickle.load(f)
    f.close()
    sys.stderr.write( "{} ID: {}\n".format( datetime.datetime.utcnow().isoformat(), j.acct['id'] ) )

    walltime = max(j.end_time - j.start_time, 0)
    
    #summaryDict['Jobid'] = j.acct['id']
    #summaryDict['picklefile'] = path + '/' + infile
    #summaryDict['walltime'] = walltime
    
    #for i in ['granted_pe', 'queue', 'exit_status', 'account', 'owner']:
    #  if i in j.acct.keys():
    #    summaryDict[i] = j.acct[i]

    if j.hosts.keys():
      summaryDict['nHosts'] = len(j.hosts)
      pass
    else:
      summaryDict['nHosts'] = 0
      summaryDict['Error'].append('No Host Data')
      sys.stderr.write( 'ERROR: No Host Data\n' )
      continue

    if 0 == walltime:
      summaryDict['Error'].append('Walltime is 0')
      sys.stderr.write( 'ERROR: Walltime is 0\n' )
      continue

    #metrics = {
    #  'intel_snb': ['LOAD_OPS_ALL', 'LOAD_OPS_L1_HIT', 'LOAD_OPS_L2_HIT', 'LOAD_OPS_LLC_HIT', 'SSE_D_ALL', 'SIMD_D_256', 'LOAD_L1D_ALL', 'STALLS', 'INSTRUCTIONS_RETIRED', 'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'],
    #  'intel_snb_cbo': ['RxR_OCCUPANCY', 'LLC_LOOKUP', 'COUNTER0_OCCUPANCY', 'CLOCK_TICKS'],
    #  'intel_snb_hau': ['READ_REQUESTS', 'WRITE_REQUESTS', 'CLOCKTICKS', 'IMC_WRITES'],
    #  'intel_snb_imc': ['CAS_READS', 'CAS_WRITES', 'ACT_COUNT', 'PRE_COUNT_ALL', 'CYCLES'],
    #  'intel_snb_pcu': ['MAX_TEMP_CYCLES', 'MAX_POWER_CYCLES', 'MIN_IO_CYCLES', 'MIN_SNOOP_CYCLES', 'C3_CYCLES', 'C6_CYCLES'],
    #  'intel_snb_r2pci': ['TRANSMITS', 'DATA_USED', 'ADDRESS_USED', 'ACKNOWLEDGED_USED'],
    #  'block': ['rd_ios', 'rd_sectors', 'wr_ios', 'wr_sectors'],
    #  'cpu': ['system', 'user', 'idle', 'all'],
    #  'ib': ['port_rcv_pkts', 'port_rcv_data', 'port_xmit_pkts', 'port_xmit_data'],
    #  'llite': ['read_bytes', 'write_bytes'],
    #  'lnet': ['rx_msgs', 'rx_bytes', 'tx_msgs', 'tx_bytes'],
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
          summaryDict['Error'].append('summary metric ' + str(l) + ' not in the schema')
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
              rates = numpy.diff(v) * reciprocals
              series['cpu']['all'][interface].extend(rates)

            for l in indices[k].keys():
              v = j.hosts[i].stats[k][interface][:, indices[k][l]]
              if interface not in sums[k][l].keys():
                sums[k][l][interface] = 0
                series[k][l][interface] = []
              if j.get_schema(k)[l].is_event:
                # If the datatype is an event then the values are converted to rates.
                sums[k][l][interface] = sums[k][l][interface] + (v[-1]
                      - v[0]) / walltime  # divide walltime here, to avoid overflow in summation
                if len(reciprocals) == len(v) - 1:
                  rates = numpy.diff(v) * reciprocals
                  series[k][l][interface].extend(rates.tolist() )
              else:
                # else the datatype is an instantaneous value such as memory, load ave or disk usage.
                if 2 < len(v):

                 # for memory metrics, throw away the first (and the last, if possible) results
                 # since they are measured at the endpoints of a job

                  v = v[1:len(v) - 1]
                else:
                  v = v[1:len(v)]
                series[k][l][interface].extend(v / nCoresPerSocket)

    if 0 < nCores_allhosts:

    # SSE_FLOPS

      if 'intel_snb' in sums.keys():

        if 'SSE_D_ALL' in sums['intel_snb'] and 'SIMD_D_256' in sums['intel_snb']:
          s1 = 0
          s2 = 0
          v = []
          for l in sums['intel_snb']['SSE_D_ALL'].keys():
            # iterate all CPU cores
            s1 += sums['intel_snb']['SSE_D_ALL'][l]
            s2 += sums['intel_snb']['SIMD_D_256'][l]
            summaryDict['FLOPS'] = ( 2 * ( s1/nCores_allhosts ) ) + ( 4 * ( s2/nCores_allhosts ) )
        else:
          summaryDict['FLOPS'] = { 'error': 'unavailable' }

      elif 'intel_pmc3' in sums.keys():

        s = 0
        v = []
        for l in sums['intel_pmc3']['PMC2'].keys():
          # iterate all CPU cores
          s += sums['intel_pmc3']['PMC2'][l]
          v.extend(series['intel_pmc3']['PMC2'][l])
        if v:
          v = calculate_stats(v)
          if 0 < v['max']:
            v['overall_avg'] = s / nCores_allhosts
            summaryDict['FLOPS'] = v

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

  # deal with general cases

    for l in sums.keys():
      for k in sums[l].keys():
        for i in sums[l][k].keys():
          v = calculate_stats(series[l][k][i])
          #if 0 < v['max']:
          v['overall_avg'] = sums[l][k][i] / nHosts
          summaryDict[l + '.' + i + '.' + k] = v
  
  # add in lariat data
  if lariatcache != None:
      lariatdata = lariatcache.find(j.id, j.acct['start_time'])
      if lariatdata != None:
          summaryDict['lariat'] = lariatdata
      else:
          summaryDict['Error'].append("Lariat data not found")

  # add hosts
  summaryDict['hosts'] = []
  for i in j.hosts.keys():
    summaryDict['hosts'].append(i)
  
  # add account info from slurm accounting files
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
      summaryDict['Error'].append("schema data not found")

  summaryDict['summary_version'] = "0.9.1"

  if len(summaryDict['Error']) == 0:
    del summaryDict['Error']

  # print out json to stdout
  try:
      with open(outputfilename, "wb") as fp:
        json.dump(summaryDict, fp, indent=2)
  except Exception as e:
      print json.dumps(summaryDict, indent=2)

if __name__ == '__main__':
  main()
