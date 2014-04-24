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


def summarize(j, lariatcache):

    summaryDict = {}
    summaryDict['Error'] = []

    metrics = None
    statsOk = True

    aggregates = [ "sched", "intel_pmc3", "intel_uncore", "intel_snb", "intel_snb_cbo", "intel_snb_imc" ]
    conglomerates = [ "irq" ]

    sys.stderr.write( "{} ID: {}\n".format( datetime.datetime.utcnow().isoformat(), j.acct['id'] ) )

    walltime = max(j.end_time - j.start_time, 0)

    if j.hosts.keys():
        summaryDict['nHosts'] = len(j.hosts)
    else:
        summaryDict['nHosts'] = 0
        summaryDict['Error'].append('No Host Data')

    if 0 == walltime:
        summaryDict['Error'].append('Walltime is 0')
        sys.stderr.write( 'ERROR: Walltime is 0\n' )

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
                        deltas = numpy.diff(v)
                        if 0 in deltas:
                            summaryDict['Error'].append("host {}, cpu {} unusual halted clock".format(j.hosts[i].name, interface) )
                            statsOk = False

                        rates = deltas * reciprocals

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

    if 0 < nCores_allhosts and statsOk:

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

            if 'PMC2' in sums['intel_pmc3']:
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
                        key = device + '-' + interface
                        summaryDict[ key.replace(".","-") ] = v
                del sums[device]
    
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
                        key = device + '-' + interface
                        summaryDict[ key.replace(".","-") ] = v[index]
                del sums[device]

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
                summaryDict['mem-used'] = res
            res = calculate_stats([a - b - c for (a, b, c) in zip(v, v2, v3)])
            if 0 < res['max']:
                summaryDict['mem-used_minus_diskcache'] = res

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
                    summaryDict['cpu-'+l] = v2

        del sums['cpu']  # we are done with 'cpu'
        del sums['mem']  # we are done with 'mem'

    # deal with general cases

    if statsOk:
        for l in sums.keys():
            for k in sums[l].keys():
                for i in sums[l][k].keys():
                    v = calculate_stats(series[l][k][i])
                    #if 0 < v['max']:
                    v['overall_avg'] = sums[l][k][i] / nHosts
                    key = l + '-' + i + '-' + k
                    summaryDict[key.replace(".","-")] = v

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
    #if statsOk:
    #    summaryDict['schema'] = {}
    #    try:
    #        for k in metrics:
    #            for l in metrics[k]:
    #                if l in j.get_schema(k):
    #                    if k not in summaryDict['schema']:
    #                        summaryDict['schema'][k]={}
    #                    summaryDict['schema'][k][l] = str( j.get_schema(k)[l] )
    #    except:
    #        if (summaryDict['nHosts'] != 0):
    #            sys.stderr.write( 'ERROR: %s\n' % sys.exc_info()[0] )
    #            sys.stderr.write( '%s\n' % traceback.format_exc() )
    #            summaryDict['Error'].append("schema data not found")

    summaryDict['summary_version'] = "0.9.3"
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
