#!/opt/apps/python/2.7.1/bin/python
import argparse, datetime, gzip, os, signal, string, subprocess, sys, time
# signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# TODO Handle changes in schema.
# TODO Sanity check on rollover.
# TODO Check that input values are not wider than allowed.

opt_verbose = True # XXX
prog = os.path.basename(sys.argv[0])
if prog == "":
    prog = "***"

def trace(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)

def error(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    
def fatal(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    sys.exit(1)


archive_dir = "/scratch/projects/tacc_stats/archive"
STATS_PROGRAM = "tacc_stats" # XXX
STATS_VERSION = "1.0.1" # XXX
FILE_TIME_MAX = 86400 + 3600 # XXX
SF_SCHEMA_CHAR = '!'
SF_DEVICES_CHAR = '@'
SF_COMMENT_CHAR = '#'
SF_PROPERTY_CHAR = '$'
SF_MARK_CHAR = '%'

# amd64
# define PERF_EVENT(event_select, unit_mask) \
#  ( (event_select & 0xFF) \
#  | (unit_mask << 8) \
#  | (1UL << 16) /* Count in user mode (CPL == 0). */ \
#  | (1UL << 17) /* Count in OS mode (CPL > 0). */ \
#  | (1UL << 22) /* Enable. */ \
#  | ((event_select & 0xF00) << 24) \
#  )

def amd64_perf_event(event_select, unit_mask):
    return (event_select & 0xFF) | (unit_mask << 8) | (1L << 16) | (1L << 17) | (1L << 22) | ((event_select & 0xF00) << 24)

#define DRAMaccesses   PERF_EVENT(0xE0, 0x07) /* DCT0 only */
#define HTlink0Use     PERF_EVENT(0xF6, 0x37) /* Counts all except NOPs */
#define HTlink1Use     PERF_EVENT(0xF7, 0x37) /* Counts all except NOPs */
#define HTlink2Use     PERF_EVENT(0xF8, 0x37) /* Counts all except NOPs */
#define UserCycles    (PERF_EVENT(0x76, 0x00) & ~(1UL << 17))
#define DCacheSysFills PERF_EVENT(0x42, 0x01) /* Counts DCache fills from beyond the L2 cache. */
#define SSEFLOPS       PERF_EVENT(0x03, 0x7F) /* Counts single & double, add, multiply, divide & sqrt FLOPs. */

dram_accesses = amd64_perf_event(0xE0, 0x07)
ht_link_0_use = amd64_perf_event(0xF6, 0x37)
ht_link_1_use = amd64_perf_event(0xF7, 0x37)
ht_link_2_use = amd64_perf_event(0xF8, 0x37)
user_cycles = amd64_perf_event(0x76, 0x00) & ~(1L << 17)
dcache_sys_fills = amd64_perf_event(0x42, 0x01)
sse_flops = amd64_perf_event(0x03, 0x7F)

job_info_cmd = "./tacc_job_info" # XXX
def get_job_info(id):
    id = str(id)
    info = {}
    info_proc = subprocess.Popen([job_info_cmd, id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in info_proc.stdout:
        key, sep, val = line.strip().partition(" ")
        if key != "":
            info[key] = val
    info_id = info.get("id")
    if not info_id:
        # FIXME Prints "cannot get info for job `1971376': tacc_job_info: cannot find accounting data for job 1971376".
        info_err = ""
        for line in info_proc.stderr:
            info_err += line
        error("cannot get info for job `%s': %s\n", id, info_err.strip())
         # return None
    if info_id != id:
        error("%s returned info for wrong job, requested `%s', received `%s'\n", job_info_cmd, id, info_id)
        # return None
    return info


class Job(object):
    def __init__(self, id, info=None):
        self.id = str(id)
        self.begin = 0
        self.end = 0
        self.types = {}
        self.hosts = {}
        self.bad_hosts = {}
        self.info = info
        if not self.info:
            self.info = get_job_info(self.id)
        if not self.info:
            return
        self.id = self.info["id"]
        self.begin = long(self.info["begin"])
        self.end = long(self.info["end"])
        host_list = self.info["hosts"].split()
        if len(host_list) == 0:
            error("empty host list for job `%s'\n", id)
        for host in host_list:
            entry = HostEntry(self, host)
            if len(entry.records) < 2: # BLECH.
                self.bad_hosts[host] = entry
                continue
            self.hosts[host] = entry
            for type_name, type_data in entry.types.iteritems():
                for dev in type_data.devs:
                    self.types[type_name].devs.add(dev)
        # TODO Warn about bad hosts.
    def get_schema(self, type_name, schema_desc):
        # TODO Warn about schema changes.
        data = self.types.get(type_name)
        if not data:
            data = JobTypeData(type_name)
            self.types[type_name] = data
        schema = data.schemas.get(schema_desc)
        if not schema:
            schema = Schema(type_name, schema_desc)
            data.schemas[schema_desc] = schema
        return schema


class JobTypeData(object):
    def __init__(self, name):
        self.name = name
        self.schemas = {}
        self.devs = set()


def get_stats_paths(job, host_name):
    files = []
    host_dir = os.path.join(archive_dir, host_name)
    trace("host_name `%s', host_dir `%s'\n", host_name, host_dir)
    for dent in os.listdir(host_dir):
        base, dot, ext = dent.partition(".")
        if not base.isdigit():
            continue
        # TODO Pad end.
        # Prune to files that might overlap with job.
        file_begin = long(base)
        file_end_max = file_begin + FILE_TIME_MAX
        if max(job.begin, file_begin) <= min(job.end, file_end_max):
            files.append((file_begin, os.path.join(host_dir, dent)))
    files.sort(key=lambda tup: tup[0])
    # trace("host_name `%s', files `%s'\n", host_name, files)
    return [tup[1] for tup in files]


class HostEntry(object):
    def __init__(self, job, name):
        self.job = job
        self.name = name
        self.types = {}
        self.records = []
        self.marks = {}
        end_mark = "end %s" % job.id
        self.stats_file_paths = get_stats_paths(job, self.name)
        if len(self.stats_file_paths) == 0:
            error("host `%s' has no stats files overlapping job `%s'\n", self.name, job.id)
        for path in self.stats_file_paths:
            self.read_stats_file(gzip.open(path))
            if end_mark in self.marks:
                break
        # TODO Check for begin, end mark.
    def read_stats_file(self, file):
        job_id = self.job.id
        rec = None
        rec_job_id = ""
        for line in file:
            c = line[0]
            if c.isalpha():
                if rec_job_id == job_id:
                    tdv = line.split()
                    self.add_stats(rec, tdv[0], tdv[1], map(long, tdv[2:]))
                elif len(self.records) != 0:
                    return # We're done.
            elif c.isdigit():
                str_time, rec_job_id = line.split()
                if rec_job_id == job_id:
                    rec = self.new_record(long(str_time))
            elif c.isspace():
                pass
            elif c == SF_SCHEMA_CHAR:
                type_name, sep, schema_desc = line[1:].partition(" ")
                self.add_type(type_name, schema_desc)
            elif c == SF_DEVICES_CHAR:
                pass # TODO
            elif c == SF_COMMENT_CHAR:
                pass
            elif c == SF_PROPERTY_CHAR:
                pass # TODO
            elif c == SF_MARK_CHAR:
                if rec_job_id == job_id:
                    self.add_mark(rec, line[1:].strip())
            else:
                error("%s: unrecognized directive `%s'\n", file.name, line.strip())
    def add_type(self, type_name, schema_desc):
        type_data = self.types.get(type_name)
        if not type_data:
            schema = self.job.get_schema(type_name, schema_desc)
            type_data = HostTypeData(schema)
            self.types[type_name] = type_data
        if type_data.schema.desc != schema_desc: # BLECH.
            error("schema changed for type `%s', host `%s'\n", type_name, self.name)
    def add_stats(self, rec, type_name, dev, vals):
        type_data = self.types.get(type_name)
        if not type_data:
            error("no data for type `%s', host `%s', dev `%s'\n", type_name, self.name, dev)
            return
        type_ent = rec.types.setdefault(type_name, {})
        type_ent[dev] = type_data.schema.process(type_data, dev, vals)
    def new_record(self, time):
        rec = Record(time - self.job.begin)
        self.records.append(rec)
        return rec
    def add_mark(self, rec, mark):
        self.marks.setdefault(mark, []).append(rec)


class Record(object):
    def __init__(self, time):
        self.time = time
        self.types = {}


class HostTypeData(object):
    def __init__(self, schema):
        self.schema = schema
        self.devs = {}


class Schema(object):
    def __init__(self, name, desc):
        self.name = name
        self.desc = desc
        self.entries = []
        self.keys = {}
        for index, entry_desc in enumerate(desc.split()):
            entry = SchemaEntry(index, entry_desc)
            self.keys[entry.key] = entry
            self.entries.append(entry)
    def process(self, data, dev, vals):
        res = []
        tup = data.devs.get(dev)
        if not tup:
            tup = data.devs[dev] = (list(vals), list(vals))
        base, prev = tup
        for entry in self.entries:
            i = entry.index
            val = vals[i]
            if entry.event:
                if val < prev[i]:
                    width = entry.width or 64 # XXX
                    if abs(val - prev[i]) < 0.25 * (2.0 ** width): #XXX
                        trace("spurious rollover on type `%s', dev `%s', counter `%s', val %d, prev, %d\n",
                              self.name, dev, entry.key, val, prev[i])
                        val = prev[i]
                    else:
                        if self.name != "amd64_pmc": # XXX
                            trace("rollover on type `%s', dev `%s', counter `%s', val %d, prev, %d\n",
                                  self.name, dev, entry.key, val, prev[i])
                        base[i] -= 1L << width
                val -= base[i]
            prev[i] = vals[i]
            if entry.mult:
                val *= entry.mult
            res.append(val)
        return res


class SchemaEntry(object):
    def __init__(self, index, desc):
        opt_lis = desc.split(',')
        self.key = opt_lis[0]
        self.index = index
        self.control = False
        self.event = False
        self.width = None
        self.mult = None
        self.unit = None
        # TODO Add gauge.
        for opt in opt_lis[1:]:
            if len(opt) == 0:
                continue
            elif opt[0] == 'C':
                self.control = True
            elif opt[0] == 'E':
                self.event = True
            elif opt[0:2] == 'W=':
                self.width = int(opt[2:])
            elif opt[0:2] == 'U=':
                i = 2
                while i < len(opt) and opt[i].isdigit():
                    i += 1
                if i > 2:
                    self.mult = int(opt[2:i])
                if i < len(opt):
                    self.unit = opt[i:]
                if self.unit == "KB":
                    self.mult = 1024
                    self.unit = "B"
            else:
                error("unrecognized option `%s' in schema entry spec `%s'\n", opt, desc)

