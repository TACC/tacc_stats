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

def compute_ratio(stats, indices, numerator, denominator, out):
    if numerator in indices and denominator in indices and 'ERROR' not in indices:
        cidx = indices[numerator]
        insidx = indices[denominator]
        if stats[-1, insidx] > 0:
            out.append( 1.0 * stats[-1,cidx] / stats[-1, insidx] )

def compute_sum(stats, indices, a, b, out, hostwalltime):
    if a in indices and b in indices and 'ERROR' not in indices:
        cidx = indices[a]
        insidx = indices[b]
        out.append( (1.0 * stats[-1,cidx] + 1.0 * stats[-1, insidx])/ hostwalltime )

def addtoseries(interface, series, enties, data):
    if interface not in series:
        series[interface] = data
        enties[interface] = 1
    else:
        series[interface] += data
        enties[interface] += 1

def converttooutput(series, summaryDict, j):
    for l in series.keys():
        for k in series[l].keys():
            if isinstance(series[l][k], dict):
                for i in series[l][k].keys():
                    v = calculate_stats(series[l][k][i])
                    addinstmetrics(summaryDict,j.overflows, l, i, k, v)
            else:
                v = calculate_stats(series[l][k])
                addmetrics(summaryDict,j.overflows, l, k, v)


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
    res = { }

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
        res['krt'] = v_kurt
        res['min'] = float(v_min)
        res['skw'] = v_skew
        res['cnt'] = len(v)
        if res['min'] == res['max']:
            res['med'] = res['min']
            res['std'] = 0.0
        else:
            res['med'] = float(numpy.median(v, axis=0))
            if len(v) > 2:
                res['std'] = scipy.stats.tstd(v)

        if 0 < v_avg:
            res['cov'] = math.sqrt(v_var) / v_avg

    return res

def addinstmetrics(summary, overflows, device, interface, instance, values):

    key = (device + "-" + interface + "-" + instance).replace(".", "-")

    data = values

    if COMPACT_OUTPUT and 'avg' in values and values['avg'] == 0.0:
        return

    if device in overflows and interface in overflows[device] and instance in overflows[device][interface]:
        data = { "error": 2048, "error_msg": "Counter overflow on hosts " + str(overflows[device][interface][instance]) }
    
    if device not in summary:
        summary[device.replace(".","-")] = {}
    if interface not in summary[device]:
        summary[device.replace(".","-")][interface.replace(".","-")] = {}

    summary[device.replace(".","-")][interface.replace(".","-")][instance.replace(".","-")] = data

def addmetrics(summary, overflows, device, interface, values):

    data = values

    if COMPACT_OUTPUT and 'avg' in values and values['avg'] == 0.0:
        return

    if device in overflows:
        # The cpu device is special because all of the counters are summed together - an overflow in one
        # impacts all cpu metrics.
        if (device == "cpu") or ( interface in overflows[device]):
            data = { "error": 2048, "error_msg": "Counter overflow on hosts " + str(overflows[device]) }
    
    if device not in summary:
        summary[device.replace(".","-")] = {}

    summary[device.replace(".","-")][interface.replace(".","-")] = data

def summarize(j, lariatcache):

    summaryDict = {}
    summaryDict['Error'] = list(j.errors)

    metrics = None
    statsOk = True

    perinterface = [ "cpu", "mem", "sched", "intel_pmc3", "intel_uncore", "intel_snb", "intel_snb_cbo", "intel_snb_imc", "intel_snb_pcu", "intel_snb_hau", "intel_snb_qpi", "intel_snb_r2pci" ]
    conglomerates = [ "irq" ]

    # The ib and ib_ext counters are known to be incorrect on all tacc_stats systems
    ignorelist = [ "ib", "ib_ext" ]

    # nfs metrics take up alot of space
    ignorelist.append("nfs")
    ignorelist.append("osc")
    ignorelist.append("mdc")

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
    totals = {}
    series = {}  # we keep the time series data here, because we need to calculate min/max/median & 1/2/3/4th order of moments
    enties = {}
    isevent = {}

    for metricname, metric in metrics.iteritems():
        indices[metricname] = {}
        isevent[metricname] = {}
        totals[metricname] = {}
        series[metricname] = {}
        enties[metricname] = {}
        for interface in metric:
            try:
                if interface in j.get_schema(metricname):
                    indices[metricname][interface] = j.get_schema(metricname)[interface].index
                    isevent[metricname][interface] = j.get_schema(metricname)[interface].is_event
            except:
                sys.stderr.write( 'ERROR: summary metric ' + str(interface) + ' not in the schema\n' )
                sys.stderr.write( 'ERROR: %s\n' % sys.exc_info()[0] )
                sys.stderr.write( '%s\n' % traceback.format_exc() )
                summaryDict['Error'].append('summary metric ' + str(interface) + ' not in the schema')

    nHosts = 0
    corederived = { "cpicore": [], "cpiref": [], "cpldref": [] }
    socketderived = { "membw": [] }

    # Naming convention:
    #  metricname - the name of the metric (such as cpu, mem etc).
    #  interface  - the interface exposed for the metric (such as user, system)
    #  device     - the name of the device (ie cpu0, numanode0, eth0 )

    for host in j.hosts.itervalues():  # for all the hosts present in the file
        nHosts += 1
        nCoresPerSocket = 1
        hostwalltime = host.times[-1] - host.times[0]

        if abs(hostwalltime - walltime) > TIMETHRESHOLD:
            summaryDict['Error'].append("Large discrepency between job account walltime and tacc_stats walltime for {}. {} != {}.".format(host.name, walltime, hostwalltime) )

        if hostwalltime < MINTIMEDELTA:
            summaryDict['Error'].append("Insufficient data points for host {}. {}".format(host.name, host.times) )
            continue
        
        if 'cpu' in host.stats.keys() and 'mem' \
          in host.stats.keys():
            nCoresPerSocket = len(host.stats['cpu']) \
              // len(host.stats['mem'])

        for metricname in indices.keys():
            if metricname in ignorelist:
                continue
            if metricname not in host.stats.keys():
                continue

            for device in host.stats[metricname].keys():
                for interface, index in indices[metricname].iteritems():

                    if isevent[metricname][interface]:
                        # Counter-type metrics get converted into average rates

                        if metricname in perinterface:
                            # Generate per-interface values
                            if interface not in totals[metricname]:
                                totals[metricname][interface] = []

                            totals[metricname][interface].append( host.stats[metricname][device][-1,index] / hostwalltime )
                        else:
                            # Generate values for all enties
                            if interface not in totals[metricname]:
                                totals[metricname][interface] = {}
                            if device not in totals[metricname][interface]:
                                totals[metricname][interface][device] = []
                            
                            totals[metricname][interface][device].append( host.stats[metricname][device][-1,index] / hostwalltime  )
                    else:
                        # Instantaneous metrics have all timeseries values processed except
                        # the first and last
                        ndatapoints = len(host.stats[metricname][device][:,index])
                        if ndatapoints > 2:
                            end = ndatapoints - 1
                        else:
                            end = ndatapoints

                        data = host.stats[metricname][device][1:ndatapoints,index]

                        # Special case - memory is raw per node, but averaged per core
                        if metricname == "mem":
                            data /= nCoresPerSocket

                        if metricname in perinterface:
                            addtoseries(interface, series[metricname], enties[metricname], data)
                        else:
                            # Generate values for all enties
                            if interface not in series[metricname]:
                                series[metricname][interface] = {}
                                enties[metricname][interface] = {}
                            if device not in series[metricname][interface]:
                                series[metricname][interface][device] = data
                                enties[metricname][interface][device] = 1
                            else:
                                series[metricname][interface][device] += data
                                enties[metricname][interface][device] += 1
                # end for interface, index in indices[metricname].iteritems()

                # Special cases
                if metricname == "cpu":
                    if "all" not in totals["cpu"]:
                        totals["cpu"]["all"] = []
                    totals["cpu"]["all"].append( sum( 1.0 * host.stats[metricname][device][-1,:] / hostwalltime) )

                elif metricname == "intel_snb":
                    compute_ratio(host.stats[metricname][device], indices[metricname], 'CLOCKS_UNHALTED_CORE', 'INSTRUCTIONS_RETIRED', corederived["cpicore"])
                    compute_ratio(host.stats[metricname][device], indices[metricname], 'CLOCKS_UNHALTED_REF', 'INSTRUCTIONS_RETIRED', corederived["cpiref"])
                    compute_ratio(host.stats[metricname][device], indices[metricname], 'LOAD_L1D_ALL', 'CLOCKS_UNHALTED_REF', corederived["cpldref"])

                elif metricname == "intel_pmc3":
                    compute_ratio(host.stats[metricname][device], indices[metricname], 'CLOCKS_UNHALTED_CORE', 'INSTRUCTIONS_RETIRED', corederived["cpicore"])
                    compute_ratio(host.stats[metricname][device], indices[metricname], 'CLOCKS_UNHALTED_REF', 'INSTRUCTIONS_RETIRED', corederived["cpiref"])

                elif metricname == "intel_snb_imc":
                    compute_sum(host.stats[metricname][device], indices[metricname], 'CAS_READS', 'CAS_WRITES', socketderived["membw"], hostwalltime / 64.0 )

                elif metricname == "mem":
                    if 'MemUsed' in indices[metricname] and 'FilePages' in indices[metricname] and 'Slab' in indices[metricname]:

                        muindex = indices[metricname]['MemUsed']
                        fpindex = indices[metricname]['FilePages']
                        slindex = indices[metricname]['Slab']

                        ndatapoints = len(host.stats[metricname][device][:,muindex])
                        if ndatapoints > 2:
                            end = ndatapoints - 1
                        else:
                            end = ndatapoints

                        memstat = host.stats[metricname][device][1:ndatapoints,muindex] - \
                                host.stats[metricname][device][1:ndatapoints,fpindex] - \
                                host.stats[metricname][device][1:ndatapoints,slindex]

                        addtoseries("used_minus_diskcache", series[metricname], enties[metricname], memstat)

            # end for device
        # end loop over hosts

    if 'cpu' not in totals or 'all' not in totals['cpu']:
        statsOk = False
        summaryDict['Error'].append( "No CPU information" )

    # Change series values into per entity values e.g. Memory per node or IO per node
    for metricname, ifstats in series.iteritems():
        for interface, devstats in ifstats.iteritems():
            if isinstance(devstats, dict):
                for devname, dstats in devstats.iteritems():
                    dstats /= enties[metricname][interface][devname]
            else:
                devstats /= enties[metricname][interface]

    if statsOk:

        for mname, mdata in corederived.iteritems():
            # Store CPI per core
            if len(mdata) > 0:
                summaryDict[mname] = calculate_stats(mdata)
                if len(mdata) != len( totals['cpu']['all'] ):
                    summaryDict[mname]['error'] = 2
                    summaryDict[mname]['error_msg'] = 'Not all cores have counters'

        for mname, mdata in socketderived.iteritems():
            # Store socket derived metrics
            if len(mdata) > 0:
                summaryDict[mname] = calculate_stats(mdata)

        # flops
        if 'intel_snb' in totals.keys():

            if 'SSE_D_ALL' in totals['intel_snb'] and 'SIMD_D_256' in totals['intel_snb'] and 'ERROR' not in totals['intel_snb']:
                flops = 4.0 * numpy.array(totals['intel_snb']['SIMD_D_256']) + 2.0 * numpy.array(totals['intel_snb']['SSE_D_ALL'])
                summaryDict['FLOPS'] = calculate_stats(flops)
            else:
                summaryDict['FLOPS'] = { 'error': 2, "error_msg": 'Counters were reprogrammed during job' }

        # TODO Nehalem/Westmere flops


        # cpu usage
        totalcpus = numpy.array(totals['cpu']['all'])
        if min(totalcpus) < 90.0:
            summaryDict['Error'].append("Corrupt CPU counters")
            summaryDict['cpuall'] = calculate_stats(totalcpus)
        else:
            for interface, cdata in totals['cpu'].iteritems():
                if interface != "all":
                    v = calculate_stats( numpy.array(cdata) / totalcpus )
                    addmetrics(summaryDict,j.overflows, "cpu", interface, v)
        del totals['cpu']

        converttooutput(series, summaryDict, j)
        converttooutput(totals, summaryDict, j)

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

    summaryDict['summary_version'] = "0.9.19"
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
