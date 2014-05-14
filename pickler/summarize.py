#!/usr/bin/env python

import datetime
import job_stats
import math
import numpy
import os
import scipy
import sys
import json
import traceback
from scipy import stats

VERBOSE = False

# Max discrepency between walltime and records time
TIMETHRESHOLD = 60

# Minimum time difference between two consecutive data points
MINTIMEDELTA = 5

# Compact format
COMPACT_OUTPUT = True

#ignore warnings from numpy
numpy.seterr(all='ignore')

def removeDotKey(obj):

    for key in obj.keys():
        new_key = key.replace(".", "-")
        if new_key != key:
            obj[new_key] = obj[key]
            del obj[key]
    return obj

class LariatManager:
    def __init__(self, lariatpath):
        self.lariatpath = lariatpath
        self.lariatdata = dict()
        self.filesprocessed = []
        self.errors = dict()

    def find(self, jobid, jobstarttime, jobendtime):

        if jobid in self.lariatdata:
            return self.lariatdata[jobid]

        for days in (0, -1, 1):
            searchday = datetime.datetime.utcfromtimestamp(jobendtime) + datetime.timedelta(days)
            lfilename = os.path.join(self.lariatpath, searchday.strftime('%Y'), searchday.strftime('%m'), searchday.strftime('lariatData-sgeT-%Y-%m-%d.json'))
            self.loadlariat(lfilename)
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
                lariatJson = json.loads(content, object_hook=removeDotKey)

                for k,v in lariatJson.iteritems():
                    if k not in self.lariatdata:
                        self.lariatdata[k] = v[0]
                    else:
                        # Have already got a record for this job. Keep the record
                        # that has longer recorded runtime since this is probably
                        # the endofjob record.
                        if 'runtime' in v[0] and 'runtime' in self.lariatdata[k] and self.lariatdata[k]['runtime'] < v[0]['runtime']:
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

    if len(v) > 0:

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

def addmetrics(summary, metricname, values):
    key = metricname.replace(".", "-")
    
    if COMPACT_OUTPUT and 'overall_avg' in values and values['overall_avg'] == 0.0:
        summary[key] = { 'overall_avg': 0.0 }
    else:
        summary[key] = values

def summarize(j, lariatcache):

    summaryDict = {}
    summaryDict['Error'] = list(j.errors)

    metrics = None
    statsOk = True

    aggregates = [ "sched", "intel_pmc3", "intel_uncore", "intel_snb", "intel_snb_cbo", "intel_snb_imc", "intel_snb_pcu", "intel_snb_hau", "intel_snb_qpi", "intel_snb_r2pci" ]
    conglomerates = [ "irq" ]

    # The ib and ib_ext counters are known to be incorrect on all tacc_stats systems
    ignorelist = [ "ib", "ib_ext" ]

    if VERBOSE:
        sys.stderr.write( "{} ID: {}\n".format( datetime.datetime.utcnow().isoformat(), j.acct['id'] ) )

    walltime = max(j.end_time - j.start_time, 0)

    if len(j.times) == 0:
        summaryDict['Error'].append("No timestamp records")
        statsOk = False

    if j.hosts.keys():
        summaryDict['nHosts'] = len(j.hosts)
    else:
        summaryDict['nHosts'] = 0
        summaryDict['Error'].append('No Host Data')

    if 0 == walltime:
        summaryDict['Error'].append('Walltime is 0')

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

    nCores_allhosts = 0
    nHosts = 0

    for host in j.hosts.itervalues():  # for all the hosts present in the file
        nHosts += 1
        nCoresPerSocket = 1

        timedeltas = numpy.diff(host.times)
        validtimes = [ True if x > MINTIMEDELTA else False for x in timedeltas ]
        reciprocals = 1.0 / numpy.compress(validtimes, timedeltas)
        hostwalltime = host.times[-1] - host.times[0]

        if abs(hostwalltime - walltime) > TIMETHRESHOLD:
            summaryDict['Error'].append("Large discrepency between job account walltime and tacc_stats walltime for {}. {} != {}.".format(host.name, walltime, hostwalltime) )

        if len(reciprocals) == 0:
            summaryDict['Error'].append("Insufficient data points for host {}. {}".format(host.name, host.times) )
            continue
        
        if 'cpu' in host.stats.keys() and 'mem' \
          in host.stats.keys():
            nCoresPerSocket = len(host.stats['cpu']) \
              // len(host.stats['mem'])

        for k in indices.keys():
            if k in host.stats.keys() and k not in ignorelist:
                for interface in host.stats[k].keys():
                    if k == 'cpu':  # special handling for 'cpu'
                        nCores_allhosts = nCores_allhosts + 1

                        if interface not in sums['cpu']['all'].keys():
                            sums['cpu']['all'][interface] = 0
                            series['cpu']['all'][interface] = []

                        sums['cpu']['all'][interface] += sum(host.stats['cpu'][interface][-1]) / hostwalltime

                        v = [ sum(x) for x in host.stats['cpu'][interface] ]
                        deltas = numpy.diff(v)
                        rates = numpy.compress(validtimes,deltas) * reciprocals

                        if 0.0 in rates:
                            summaryDict['Error'].append("host {}, cpu {} unusual halted clock".format(host.name, interface) )
                            statsOk = False

                        series['cpu']['all'][interface].extend(rates)

                    for l in indices[k].keys():
                        v = host.stats[k][interface][:, indices[k][l]]
                        if interface not in sums[k][l].keys():
                            if j.get_schema(k)[l].is_event:
                                # Only generate the sums values for events
                                sums[k][l][interface] = 0

                            series[k][l][interface] = []
                        if j.get_schema(k)[l].is_event:
                            # If the datatype is an event then the values are converted to rates.
                            sums[k][l][interface] += (v[-1] - v[0]) / hostwalltime

                            rates = numpy.compress(validtimes, numpy.diff(v)) * reciprocals
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

    if 0 < nCores_allhosts and statsOk:

        # SSE_FLOPS

        if 'intel_snb' in sums.keys():


            if 'SSE_D_ALL' in sums['intel_snb'] and 'SIMD_D_256' in sums['intel_snb'] and 'ERROR' not in sums['intel_snb']:
                s1 = 0
                s2 = 0
                v = []
                for l in sums['intel_snb']['SSE_D_ALL'].keys():
                    # iterate all CPU cores
                    s1 += sums['intel_snb']['SSE_D_ALL'][l]
                    s2 += sums['intel_snb']['SIMD_D_256'][l]
                    summaryDict['FLOPS'] = { "value": ( 2 * ( s1/nCores_allhosts ) ) + ( 4 * ( s2/nCores_allhosts ) ) }
            else:
                summaryDict['FLOPS'] = { 'error': 2, "error_msg": 'Counters were reprogrammed during job' }

        elif 'intel_pmc3' in sums.keys():

            if 'PMC2' in sums['intel_pmc3'] and 'ERROR' not in sums['intel_pmc3']:
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

        for device in aggregates:
            if device in sums.keys():
                for interface in sums[device]:
                    s = 0
                    v = []
                    for l in sums[device][interface].keys():
                        s += sums[device][interface][l]
                        v.extend(series[device][interface][l])
                    if len(v) > 0:
                        v = calculate_stats(v)
                        if 0 < v['max']:
                            v['overall_avg'] = s / nCores_allhosts
                        addmetrics(summaryDict, device + '-' + interface, v)
                del sums[device]
                del series[device]
    
        for device in conglomerates:
            if device in sums.keys():
                s = dict()
                v = dict()
                for interface in sums[device]:
                    for index in sums[device][interface]:
                        if index not in s:
                            s[index] = 0
                            v[index] = []
                        s[index] += sums[device][interface][index]
                        v[index].extend(series[device][interface][index])
                for index in s:
                    if len(v[index]) > 0:
                        v[index] = calculate_stats(v[index])
                        if 0 < v[index]['max']:
                            v[index]['overall_avg'] = s[index] / nCores_allhosts
                        addmetrics(summaryDict, device + '-' + interface, v[index])

                del sums[device]
                del series[device]

        # memory usage

        v = []
        v2 = []
        v3 = []
        for l in series['mem']['MemUsed'].keys():

            # iterate all memory sockets

            v.extend(series['mem']['MemUsed'][l])
            v2.extend(series['mem']['FilePages'][l])
            v3.extend(series['mem']['Slab'][l])
        if v:
            res = calculate_stats(v)
            if 0 < res['max']:
                addmetrics(summaryDict, 'mem-used', res)
            res = calculate_stats([a - b - c for (a, b, c) in zip(v, v2, v3)])
            if 0 < res['max']:
                addmetrics(summaryDict, 'mem-used_minus_diskcache', res)

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

                v2 = calculate_stats( numpy.array(v2) / numpy.array(v) )
                if 0 < v2['max']:
                    v2['overall_avg'] = s2 / s
                    addmetrics(summaryDict, 'cpu-'+l, v2)

        del sums['cpu']  # we are done with 'cpu'
        del series['cpu']
        del sums['mem']  # we are done with 'mem'
        del series['mem']

    # deal with general cases

    if statsOk:
        for l in series.keys():
            for k in series[l].keys():
                for i in series[l][k].keys():
                    v = calculate_stats(series[l][k][i])
                    if l in sums and k in sums[l] and i in sums[l][k]:
                        v['overall_avg'] = sums[l][k][i] / nHosts
                    addmetrics(summaryDict,l + '-' + i + '-' + k, v)

    # add in lariat data
    if lariatcache != None:
        lariatdata = lariatcache.find(j.id, j.acct['start_time'], j.acct['end_time'])
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
    if statsOk and not COMPACT_OUTPUT:
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

    summaryDict['summary_version'] = "0.9.12"
    uniq = str(j.acct['id'])
    if 'cluster' in j.acct:
        uniq += "-" + j.acct['cluster']
    uniq += "-" + str(j.acct['end_time'])

    summaryDict['_id'] = uniq

    if len(summaryDict['Error']) == 0:
        del summaryDict['Error']


    return summaryDict

if __name__ == '__main__':
    pass
