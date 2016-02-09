import sys, csv
from dateutil.parser import parse

ftr = [3600,60,1]
def acct_reader(filename):
    acct = []
    with open(filename, "rb") as fd:
        for job in csv.DictReader(fd, delimiter = '|'):
            nodelist_str = job['NodeList']
            if '[' in nodelist_str and ']' in nodelist_str: 
                nodelist = []
                prefix, nids = nodelist_str.rstrip("]").split("[")    
                for nid in nids.split(','):
                    if '-' in nid:
                        bot, top = nid.split('-') 
                        nodelist += range(int(bot), int(top)+1)
                    else: nodelist += [nid]
                    zfac = len(str(max(nodelist)))
                    nodelist = [prefix + str(x).zfill(zfac) for x in nodelist]            
                    job['NodeList'] = nodelist
                else:
                    job['NodeList'] = [nodelist_str]

            jent = {}
            jent['id']         = job['JobID']
            jent['user']       = job['User']
            jent['project']    = job['Account']
            jent['start_time'] = parse(job['Start']).strftime('%s')
            jent['end_time']   = parse(job['End']).strftime('%s')
            jent['queue_time'] = parse(job['Submit']).strftime('%s')
            jent['queue']      = job['Partition']
            jent['name']       = job['JobName']
            jent['state']      = job['State']
            jent['nodes']      = job['NNodes']
            jent['cores']      = job['ReqCPUS']
            jent['host_list']    = job['NodeList']
            print job
            if '-' in job['Timelimit']:
                days, time = job['Timelimit'].split('-')
            else:
                time = job['Timelimit']
                days = 0
            jent['requested_time'] = (int(days) * 86400 + sum([a*b for a,b in zip(ftr, [int(i) for i in time.split(":")])]))/60
            acct += [jent]
    return acct
