#!/usr/bin/env python
import job_stats
import batch_acct
import account
import summarize
import sys
import time
import datetime
from pymongo import MongoClient
from multiprocessing import Process

PROCESS_VERSION = 3

class RateCalculator:
    def __init__(self):
        self.count = 0

    def increment(self):
        if self.count == 0:
            self.starttime = time.time()

        self.count += 1

        if (self.count % 100) == 0:
            diff = time.time() - self.starttime
            print "{} Processed {} records in {} seconds ({} per second)".format( 
                    datetime.datetime.utcnow().isoformat(), self.count, diff, 1.0 * self.count / diff )


def createsummary(totalprocs, procid):

    config = account.getconfig()
    dbconf = config['accountdatabase']
    outdbconf = config['outputdatabase']

    outclient = MongoClient(host=outdbconf['dbhost'])
    outdb = outclient[outdbconf['dbname'] ]

    ratecalc = RateCalculator()

    for resourcename, settings in config['resources'].iteritems():

        dbreader = account.DbAcct( settings['resource_id'], dbconf, PROCESS_VERSION, totalprocs, procid)

        bacct = batch_acct.factory(settings['batch_system'], settings['acct_path'], settings['host_name_ext'] )

        if settings['lariat_path'] != "":
            lariat = summarize.LariatManager(settings['lariat_path'])
        else:
            lariat = None

        dbwriter = account.DbLogger( dbconf["dbhost"], dbconf["dbname"], dbconf["tablename"] )

        for acct in dbreader.reader(1361854800):
            job = job_stats.from_acct( acct, settings['tacc_stats_home'], settings['host_list_dir'], bacct )
            summary = summarize.summarize(job, lariat)

            #----------------------------------------------------------------------
            # The following remove statement is to replace the legacy document data and
            # Will be deleted once the database has been migrated.
            outdb[resourcename].remove( {"_id": summary["acct"]["id"] } )
            #----------------------------------------------------------------------

            outdb[resourcename].update( {"_id": summary["_id"]}, summary, upsert=True )
            dbwriter.logprocessed( acct, settings['resource_id'], PROCESS_VERSION )

            ratecalc.increment()

def main():

    if len(sys.argv) == 1:
        print "Usage: " + sys.argv[0] + " [N SUBPROCESSES] [TOTAL INSTANCES] [INSTANCE ID]"
        sys.exit(1)

    nprocs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    total_instances = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    instance_id = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    total_procs = nprocs * total_instances

    if nprocs == 1:
        createsummary(None, None)
    else:
        proclist = []
        for procid in xrange(nprocs):
            print "Creating subprocess {} of {} (index {} of {})".format(procid, nprocs, (instance_id*nprocs) + procid, total_procs)
            p = Process( target=createsummary, args=(total_procs, (instance_id*nprocs) + procid) )
            p.start()
            proclist.append(p)

        for proc in proclist:
            p.join()

if __name__ == '__main__': 
    main()
