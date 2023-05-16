#!/usr/bin/env python3
import psycopg2
from pgcopy import CopyManager
import os, sys, stat
from multiprocessing import Pool, get_context
from datetime import datetime, timedelta, date
import time, string

#import pandas
#pandas.set_option('display.max_rows', 100)
from pandas import DataFrame, to_datetime, Timedelta, Timestamp, concat

from tacc_stats.analysis.gen.utils import read_sql
from tacc_stats import cfg

 #import pandas
  #pandas.set_option('display.max_rows', 100)


CONNECTION = "dbname={0} user=postgres port=5432".format(cfg.dbname)

amd64_pmc_eventmap = { 0x43ff03 : "FLOPS,W=48", 0x4300c2 : "BRANCH_INST_RETIRED,W=48", 0x4300c3: "BRANCH_INST_RETIRED_MISS,W=48", 
                       0x4308af : "DISPATCH_STALL_CYCLES1,W=48", 0x43ffae :"DISPATCH_STALL_CYCLES0,W=48" }

amd64_df_eventmap = { 0x403807 : "MBW_CHANNEL_0,W=48,U=64B", 0x403847 : "MBW_CHANNEL_1,W=48,U=64B", 0x403887 : "MBW_CHANNEL_2,W=48,U=64B" , 
                      0x4038c7 : "MBW_CHANNEL_3,W=48,U=64B", 0x433907 : "MBW_CHANNEL_4,W=48,U=64B", 0x433947 : "MBW_CHANNEL_5,W=48,U=64B", 
                      0x433987 : "MBW_CHANNEL_6,W=48,U=64B", 0x4339c7 : "MBW_CHANNEL_7,W=48,U=64B" }

intel_8pmc3_eventmap = { 0x4301c7 : 'FP_ARITH_INST_RETIRED_SCALAR_DOUBLE,W=48,U=1',      0x4302c7 : 'FP_ARITH_INST_RETIRED_SCALAR_SINGLE,W=48,U=1',
                         0x4304c7 : 'FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE,W=48,U=2', 0x4308c7 : 'FP_ARITH_INST_RETIRED_128B_PACKED_SINGLE,W=48,U=4',
                         0x4310c7 : 'FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE,W=48,U=4', 0x4320c7 : 'FP_ARITH_INST_RETIRED_256B_PACKED_SINGLE,W=48,U=8',
                         0x4340c7 : 'FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE,W=48,U=8', 0x4380c7 : 'FP_ARITH_INST_RETIRED_512B_PACKED_SINGLE,W=48,U=16', 
                         "FIXED_CTR0" : 'INST_RETIRED,W=48', "FIXED_CTR1" : 'APERF,W=48', "FIXED_CTR2" : 'MPERF,W=48' }

intel_skx_imc_eventmap = {0x400304 : "CAS_READS,W=48", 0x400c04 : "CAS_WRITES,W=48", 0x400b01 : "ACT_COUNT,W=48", 0x400102 : "PRE_COUNT_MISS,W=48"}


exclude_typs = ["ib", "ib_sw", "intel_skx_cha", "proc", "ps", "sysv_shm", "tmpfs", "vfs"]

query_create_hostdata_table = """CREATE TABLE IF NOT EXISTS host_data (
                                           time  TIMESTAMPTZ NOT NULL,
                                           host  VARCHAR(64),
                                           jid   VARCHAR(32),
                                           type  VARCHAR(32),
                                           event VARCHAR(64),
                                           unit  VARCHAR(16),                                            
                                           value real,
                                           delta real,
                                           arc   real,  
                                           UNIQUE (time, host, type, event)
                                           );"""


query_create_hostdata_hypertable = """CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE; 
                                      SELECT create_hypertable('host_data', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');
                                      CREATE INDEX ON host_data (host, time DESC);
                                      CREATE INDEX ON host_data (jid, time DESC);"""

query_create_compression = """ALTER TABLE host_data SET \
                              (timescaledb.compress, timescaledb.compress_orderby = 'time DESC', timescaledb.compress_segmentby = 'host,jid,type,event');
                              SELECT add_compression_policy('host_data', INTERVAL '12h', if_not_exists => true);"""

conn = psycopg2.connect(CONNECTION)
print(conn.server_version)
with conn.cursor() as cur:

    # This should only be used for testing and debugging purposes
    #cur.execute("DROP TABLE IF EXISTS host_data CASCADE;")

    #cur.execute(query_create_hostdata_table)
    #cur.execute(query_create_hostdata_hypertable)
    #cur.execute(query_create_compression)
    cur.execute("SELECT pg_size_pretty(pg_database_size('{0}'));".format(cfg.dbname))
    for x in cur.fetchall():
        print("Database Size:", x[0])

    cur.execute("SELECT chunk_name,before_compression_total_bytes/(1024*1024*1024),after_compression_total_bytes/(1024*1024*1024) FROM chunk_compression_stats('host_data');")
    for x in cur.fetchall():
        try: print("{0} Size: {1:8.1f} {2:8.1f}".format(*x))
        except: pass

    cur.execute("SELECT chunk_name,range_start,range_end FROM timescaledb_information.chunks WHERE hypertable_name = 'host_data';")
    for x in cur.fetchall():
        try:
            print("{0} Range: {1} -> {2}".format(*x))
        except: pass
    conn.commit()    
conn.close()

# This routine will read the file until a timestamp is read that is not in the database. It then reads in the rest of the file.
def process(stats_file):

    hostname, create_time = stats_file.split('/')[-2:]
    try:
        fdate = datetime.fromtimestamp(int(create_time))
    except: return stats_file

    fdate = datetime.fromtimestamp(int(create_time))
    
    sql = "select distinct(time) from host_data where host = '{0}' and time >= '{1}'::timestamp - interval '24h' and time < '{1}'::timestamp + interval '48h' order by time;".format(hostname, fdate)
    conn = psycopg2.connect(CONNECTION)
    
    times = [int(float(t.timestamp())) for t in read_sql(sql, conn)["time"].tolist()]
    #if len(times) > 0 and max(times) > time.time() - 600: return stats_file
    #print(times)
    with open(stats_file, 'r') as fd:
        lines = fd.readlines()

    # start reading stats data from file at first - 1 missing time
    start_idx = -1
    last_idx  = 0

    first_ts = True
    for i, line in enumerate(lines): 
        if not line[0]: continue    
        if line[0].isdigit():
            if first_ts:
                first_ts = False
                continue
            t, jid, host = line.split()
            if int(float(t)) not in times: 
                start_idx = last_idx
                break
            last_idx = i

    if start_idx == -1: return stats_file

    schema = {}
    stats  = []
    insert = False
    start = time.time()
    try:
        for i, line in enumerate(lines): 
            if not line[0]: continue

            if line[0].isalpha() and insert:
                typ, dev, vals = line.split(maxsplit = 2)        
                vals = vals.split()
                if typ in exclude_typs: continue

                # Mapping hardware counters to events 
                if typ == "amd64_pmc" or typ == "amd64_df" or typ == "intel_8pmc3" or typ == "intel_skx_imc":
                    if typ == "amd64_pmc": eventmap = amd64_pmc_eventmap
                    if typ == "amd64_df": eventmap = amd64_df_eventmap
                    if typ == "intel_8pmc3": eventmap = intel_8pmc3_eventmap
                    if typ == "intel_skx_imc": eventmap = intel_skx_imc_eventmap
                    n = {}
                    rm_idx = []
                    schema_mod = []*len(schema[typ])

                    for idx, eve in enumerate(schema[typ]):
                
                        eve = eve.split(',')[0]
                        if "CTL" in eve:
                            try:
                                n[eve.lstrip("CTL")] = eventmap[int(vals[idx])]
                            except:
                                n[eve.lstrip("CTL")] = "OTHER"                    
                            rm_idx += [idx]
                        
                        elif "FIXED_CTR" in eve: 
                            schema_mod += [eventmap[eve]]

                        elif "CTR" in eve:
                            schema_mod += [n[eve.lstrip("CTR")]]
                        else:
                            schema_mod += [eve]
                    
                    for idx in sorted(rm_idx, reverse = True): del vals[idx]
                    vals = dict(zip(schema_mod, vals))
                else:
                    # Software counters are not programmable and do not require mapping
                    vals = dict(zip(schema[typ], vals))

                rec  =  { **tags, "type" : typ, "dev" : dev }   

                for eve, val in vals.items():
                    eve = eve.split(',')
                    width = 64
                    mult = 1
                    unit = "#"
                    
                    for ele in eve[1:]:                    
                        if "W=" in ele: width = int(ele.lstrip("W="))
                        if "U=" in ele: 
                            ele = ele.lstrip("U=")
                            try:    mult = float(''.join(filter(str.isdigit, ele)))
                            except: pass
                            try:    unit = ''.join(filter(str.isalpha, ele))
                            except: pass
                    
                    stats += [ { **rec, "event" : eve[0], "value" : float(val), "wid" : width, "mult" : mult, "unit" : unit } ]
                
            elif i >= start_idx and line[0].isdigit():
                t, jid, host = line.split()
                insert = True
                tags = { "time" : float(t), "host" : host, "jid" : jid }
            elif line[0] == '!':
                label, events = line.split(maxsplit = 1)
                typ, events = label[1:], events.split()
                schema[typ] = events 
        
    except:
        print("Possibly corrupt file: %s" % stats_file)
        return(stats_file)

    stats = DataFrame.from_records(stats)
    if stats.empty: 
        return(stats_file)

    # Always drop the first timestamp. For new file this is just first timestamp (at random rotate time). 
    # For update from existing file this is timestamp already in database.
    
    # compute difference between time adjacent stats. if new file first na time diff is backfilled by second time diff
    stats["delta"] = (stats.groupby(["host", "type", "dev", "event"])["value"].diff())

    # correct stats for rollover and units (must be done before aggregation over devices)
    stats["delta"].mask(stats["delta"] < 0, 2**stats["wid"] + stats["delta"], inplace = True)
    stats["delta"] = stats["delta"] * stats["mult"]
    del stats["wid"], stats["mult"]

    # aggregate over devices
    stats = stats.groupby(["host", "jid", "type", "event", "unit", "time"]).sum().reset_index()            
    stats = stats.sort_values(by=["host", "type", "event", "time"])
    
    # compute average rate of change. 
    deltat = stats.groupby(["host", "type", "event"])["time"].diff()
    stats["arc"] = stats["delta"]/deltat
    stats["time"] = to_datetime(stats["time"], unit = 's').dt.tz_localize('UTC').dt.tz_convert('US/Central')
    
    # drop rows from first timestamp
    stats = stats.dropna()
    print("processing time for {0} {1:.1f}s".format(stats_file, time.time() - start))

    # bulk insertion using pgcopy
    sqltime = time.time()
    mgr = CopyManager(conn, 'host_data', stats.columns)
    try:
        mgr.copy(stats.values.tolist())
    except Exception as e:
         print("error: mgr.copy failed: ", str(e))
        conn.close()
        return stats_file

    conn.commit()
    #print("sql insert time for {0} {1:.1f}s".format(stats_file, time.time() - sqltime))

    conn.close()
    return stats_file

if __name__ == '__main__':

    #while True:

        #################################################################


        try:
            startdate = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        except: 
            startdate = datetime.combine(datetime.today(), datetime.min.time())
        try:
            enddate   = datetime.strptime(sys.argv[2], "%Y-%m-%d")
        except:
            enddate = startdate + timedelta(days = 1)

        if (len(sys.argv) > 1):  
            if sys.argv[1] == 'all':
                startdate = 'all'
                enddate = datetime.combine(datetime.today(), datetime.min.time()) - timedelta(days = 1)

        print("###Date Range of stats files to ingest: {0} -> {1}####".format(startdate, enddate))
        #################################################################

        # Parse and convert raw stats files to pandas dataframe
        start = time.time()
        directory = cfg.archive_dir

        stats_files = []
        for entry in os.scandir(directory):
            if entry.is_file() or not entry.name.startswith("c"): continue
            for stats_file in os.scandir(entry.path):
                if startdate == 'all':
                    stats_files += [stats_file.path]
                    continue
                if not stats_file.is_file() or stats_file.name.startswith('.'): continue
                if stats_file.name.startswith("current"): continue
                try:
                    fdate = datetime.fromtimestamp(int(stats_file.name))
                except: continue
                if  fdate <= startdate - timedelta(days = 1) or fdate > enddate: continue
                stats_files += [stats_file.path]

        print("Number of host stats files to process = ", len(stats_files))

        with Pool(processes = 2) as pool:
            for i in pool.imap_unordered(process, stats_files):
                print("[{0:.1f}%] completed".format(100*stats_files.index(i)/len(stats_files)), end = "\r")
            pool.terminate()

        print("loading time", time.time() - start)


