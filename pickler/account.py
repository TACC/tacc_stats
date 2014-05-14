#!/usr/bin/env python

import MySQLdb as mdb
import os.path
import batch_acct
import json
import sys
import time

VERSION_NUMBER = 1

class DbInterface:
    def __init__(self, dbname, tablename, mydefaults):

        self.con = mdb.connect(db=dbname, read_default_file=mydefaults)
        self.tablename = tablename
        self.query = "INSERT INTO " + tablename + " (resource_id,cluster,local_job_id,start_time_ts,end_time_ts,record,ingest_version) VALUES(%s,%s,%s,%s,%s,COMPRESS(%s)," + str(VERSION_NUMBER) + ")"
        self.buffered = 0

    def resettable(self,dropexisting = False):
        cur = self.con.cursor()
        if dropexisting:
            cur.execute("DROP TABLE IF EXISTS " + self.tablename )

        cur.execute("CREATE TABLE IF NOT EXISTS " + self.tablename + "(" + \
                "resource_id INT NOT NULL,"  + \
                "local_job_id INT NOT NULL," + \
                "cluster VARCHAR(32) NOT NULL," + \
                "start_time_ts INT NOT NULL," + \
                "end_time_ts INT NOT NULL," + \
                "process_version INT NOT NULL DEFAULT -1," + \
                "process_timestamp TIMESTAMP," + \
                "ingest_version INT NOT NULL," + \
                "record BLOB," + \
                "UNIQUE (resource_id,local_job_id,cluster,end_time_ts)," + \
                "INDEX (end_time_ts,resource_id,process_version)," + \
                "INDEX (resource_id,process_version)" + \
                ") " )

    def insert(self, data):
        cur = self.con.cursor()
        try:
            cur.execute(self.query, data)
        except mdb.IntegrityError as e:
            if e[0] != 1062:
                raise e
            # else:
                # Todo - check that the blobs match on duplicate records

        self.buffered += 1
        if self.buffered > 100:
            self.con.commit()
            self.buffered = 0


    def postinsert(self):
        self.con.commit()

    def getmostrecent(self, resource_id):
        query = "SELECT MAX(end_time_ts) FROM " + self.tablename + " WHERE resource_id = %s"
        data = ( resource_id, )
        
        cur = self.con.cursor()
        cur.execute(query, data)
        return cur.fetchone()[0]

class DbLogger(object):
    def __init__(self, dbname, tablename, mydefaults):
        self.con = mdb.connect(db=dbname, read_default_file=mydefaults)
        self.tablename = tablename

    def logprocessed(self, acct, resource_id, version):

        query = "UPDATE " + self.tablename + " SET process_version = %s WHERE resource_id = %s AND local_job_id = %s AND cluster = %s AND end_time_ts = %s"
        cluster = acct['cluster'] if 'cluster' in acct else ""
        data = ( version, resource_id, acct['id'], cluster, acct['end_time'] )

        cur = self.con.cursor()
        cur.execute(query, data)
        self.con.commit()

class DbAcct(object):
    def __init__(self, resource_id, dbconf, process_version, totalprocs = None, procid = None):
        self.con = mdb.connect(db=dbconf['dbname'], read_default_file=dbconf['defaultsfile'])
        self.tablename = dbconf['tablename']
        self.process_version = process_version
        self.resource_id = resource_id
        self.totalprocs = totalprocs
        self.procid = procid

    def reader(self,start_time=None, end_time=None, seek=0):
        """ seek parameter is unused. It is present for API compatibilty with file batch acct class """

        query = "SELECT UNCOMPRESS(record) FROM " + self.tablename + " WHERE resource_id = %s AND process_version != %s "
        data = ( self.resource_id, self.process_version )
        if start_time != None:
            query += " AND end_time_ts >= %s "
            data = data + ( start_time, )
        if end_time != None:
            query += " AND end_time_ts < %s "
            data = data + ( end_time, )
        if self.totalprocs != None and self.procid != None:
            query += " AND (CRC32(local_job_id) %% %s) = %s"
            data = data + ( self.totalprocs, self.procid )
        query += " ORDER BY end_time_ts ASC"

        cur = self.con.cursor()
        cur.execute(query, data)

        for record in cur:
            r = json.loads(record[0])
            yield r

        
def getconfig(configfilename = "config.json"):
    
    with open(configfilename, "rb") as fp:
        config = json.load(fp)

    return config

def ingest(config, end_time):

    dbconf = config['accountdatabase']
    dbif = DbInterface(dbconf["dbname"], dbconf["tablename"], dbconf["defaultsfile"] )

    for resourcename,resource in config['resources'].iteritems():

        start_time = dbif.getmostrecent( resource['resource_id'] )
        if start_time == None:
            start_time = 0

        acctreader = batch_acct.factory( resource['batch_system'], resource['acct_path'], resource['host_name_ext'])

        for acct in acctreader.reader(start_time, end_time):

            record = []
            record.append( resource['resource_id'] )
            if 'cluster' in acct:
                record.append(acct['cluster'])
            else:
                record.append("")

            record.append( acct['id'] )
            record.append( acct['start_time'] )
            record.append( acct['end_time'] )
            record.append( json.dumps(acct) )

            dbif.insert(record)

        dbif.postinsert()


if __name__ == "__main__":

    if len(sys.argv) > 1:
        config = getconfig(sys.argv[1])
    else:
        config = getconfig()

    if len(sys.argv) > 2:
        end_time = sys.argv[2]
    else:
        end_time = int(time.time() - 2*24*60*60)

    ingest(config, end_time)
