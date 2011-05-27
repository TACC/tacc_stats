#!/opt/apps/python/2.7.1/bin/python
import argparse, datetime, gzip, os, signal, string, subprocess, sys, time
# signal.signal(signal.SIGPIPE, signal.SIG_DFL)

opt_verbose = False # XXX

prog = os.path.basename(sys.argv[0])

def trace(fmt, *args):
    if opt_verbose: # XXX
        msg = fmt % args
        sys.stderr.write(prog + ": " + msg)

def error(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    
def fatal(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    sys.exit(1)

job_info_cmd = "./tacc_job_info" # XXX
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

# TODO se_'ify members.
class SchemaEnt:
    def __init__(self, index, ent_spec):
        opt_lis = ent_spec.split(',')
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
                error("unrecognized option `%s' in schema entry spec `%s'\n", opt, ent_spec)


class Schema:
    def __init__(self, spec):
        # self.spec = spec
        self.ent_list = []
        self.key_to_ent = {}
        for ent_spec in spec.split():
            ent = SchemaEnt(len(self.ent_list), ent_spec)
            self.key_to_ent[ent.key] = ent
            self.ent_list.append(ent)


# TODO __slots__?
class Record(object):
    def __str__(self):
        return str(self.__dict__)


class RecordGroup(object):
    def __init__(self, host, time, jobid):
        self.host = host
        self.time = time
        self.marks = []
        self.st_dict = {}
        host.record_groups.append(self)
        # ...
    def __getattr__(self, name):
        return self.st_dict[str(name)] # or throw AttributeError
    def add_mark(self, mark):
        self.marks.append(mark)
    def add_record(self, name, dev, va):
        sc = self.host.sc_dict[name]
        # Check that len(vals) == len(schema)
        st = self.st_dict.get(name)
        if not st:
            self.st_dict[name] = st = {}
        st[dev] = rec = Record()
        dh = self.host.dev_hist.get((name, dev))
        if not dh:
            self.host.dev_hist[(name, dev)] = dh = [list(va), list(va)]
        for ent in sc.ent_list:
            i = ent.index
            v = va[i]
            if ent.event:
                if v < dh[1][i]:
                    width = ent.width or 64 #XXX
                    trace("rollover on type `%s', dev `%s', counter `%s'\n'", name, dev, ent.key)
                    dh[0][i] -= 1L << width
                v -= dh[0][i]
                dh[1][i] = va[i]
            if ent.mult:
                v *= ent.mult
            rec.__dict__[ent.key] = v


class JobHost(object):
    def __init__(self, job, host_name):
        self.job = job
        self.name = host_name
        self.sc_dict = {}
        self.dev_hist = {}
        self.record_groups = []
        # self.begin_mark = False
        self.end_mark = False
        # Get stats files for job + host.
        host_dir = os.path.join(archive_dir, self.name)
        trace("name `%s', host_dir `%s'\n", self.name, host_dir)
        stats_files = []
        for path in os.listdir(host_dir):
            if path[0] == '.':
                continue
            file_name, file_ext = path.split('.')
            # Prune to files that might overlap with job.
            file_begin = long(file_name)
            file_end_max = file_begin + FILE_TIME_MAX
            if max(self.job.begin, file_begin) <= min(self.job.end, file_end_max):
                full_path = os.path.join(host_dir, path)
                stats_files.append((file_begin, file_ext, full_path))
        if len(stats_files) == 0:
            error("host `%s' has no stats files overlapping job `%s'\n", self.name, self.job.id)
        stats_files.sort(key=lambda e: e[0])
        trace("host `%s', stats_files `%s'\n", self.name, stats_files)
        # Read stats files.
        for file_info in stats_files:
            self.read_stats_file(file_info[0], gzip.open(file_info[2]))
            if self.end_mark:
                break
        else:
            error("no end mark found for host `%s'\n", self.name)
    #
    def __str__(self):
        return self.name
    #
    def read_stats_header(self, file_time, iter):
        for line in iter:
            c = line[0]
            if c == SF_SCHEMA_CHAR:
                nss = line[1:].strip().split(" ", 1)
                self.sc_dict[nss[0]] = Schema(nss[1])
            elif c == SF_DEVICES_CHAR:
                pass # TODO
            elif c == SF_COMMENT_CHAR:
                pass
            elif c == SF_PROPERTY_CHAR:
                pass # TODO
            else:
                error("unrecognized directive `%s'\n", line)
    #
    def read_stats_file(self, file_time, file):
        file_header = []
        for line in file:
            line = line.strip()
            if len(line) == 0:
                break # End of header.
            file_header.append(line)
        rec_time = file_time
        rec_jobid = None
        for line in file:
            line = line.strip()
            if len(line) == 0:
                continue
            if line[0].isdigit():
                (str_rec_time, rec_jobid) = line.split(" ", 1)
                rec_time = long(str_rec_time)
                if rec_jobid == self.job.id:
                    break
        if rec_jobid != self.job.id:
            return
        # OK, we found some records belonging to the job.
        self.read_stats_header(file_time, file_header)
        group = RecordGroup(self, rec_time, rec_jobid)
        for line in file:
            line = line.strip()
            if len(line) == 0:
                continue
            c = line[0]
            if c.isdigit():
                (str_rec_time, rec_jobid) = line.split()
                rec_time = long(str_rec_time)
                trace("rec_jobid `%s'\n", rec_jobid)
                if rec_jobid != self.job.id:
                    return # The end.
                group = RecordGroup(self, rec_time, rec_jobid)
            elif c == SF_COMMENT_CHAR:
                pass
            elif c == SF_MARK_CHAR:
                mark = line[1:].strip()
                if mark == "end %s" % self.job.id:
                    self.end_mark = True
                group.add_mark(mark)
            elif c.isalpha():
                ndv = line.split()
                group.add_record(ndv[0], ndv[1], map(long, ndv[2:]))
            else:
                error("unrecognized header directive `%s'\n", line)


class JobStats(object):
    # TODO Caching.
    # TODO Owner, ...
    # TODO __str__
    def __init__(self, id):
        self.id = str(id)
        self.begin = None
        self.end = None
        self.hosts = []
        self.summary_cache = None
        # Get job begin, end, and hosts.
        info_proc = subprocess.Popen([job_info_cmd, self.id], stdout=subprocess.PIPE)
        info_proc_out, info_proc_err = info_proc.communicate()
        info = info_proc_out.split()
        if len(info) < 2 or not info[0].isdigit() or not info[1].isdigit():
            error("cannot get info for job `%s': %s\n", self.id, info_proc_err.strip())
            return
        if len(info) == 2:
            error("%s returned empty host list for job `%s'\n", job_info_cmd, self.id)
            return
        self.begin = long(info[0])
        self.end = long(info[1])
        trace("jobid `%s', begin %d, end %d\n", self.id, self.begin, self.end)
        for host in info[2:]:
            self.hosts.append(JobHost(self, host))
    def summary(self):
        def sum_event(type, key):
            return sum(v.__dict__[key] for h in self.hosts for v in h.record_groups[-1].st_dict[type].values())
        if not self.summary_cache:
            sc = self.summary_cache = {}
            sc["nr_collects"] = sum(len(h.record_groups) for h in self.hosts)
            sc["user_cycles"] = sum_event("amd64_pmc", "CTR1")
            sc["dcache_sys_fills"] = sum_event("amd64_pmc", "CTR2")
            sc["sse_flops"] = sum_event("amd64_pmc", "CTR3")
            sc["user_ticks"] = sum_event("cpu", "user")
            sc["system_ticks"] = sum_event("cpu", "system")
            sc["idle_ticks"] = sum_event("cpu", "idle")
            sc["nr_forks"] = sum_event("ps", "processes")
            sc["nr_ctxt_sw"] = sum_event("ps", "ctxt")
            for key in "tx_bytes", "rx_bytes":
                sc["lnet:" + key] = sum_event("lnet", key)
            for key in "open", "close", "read_bytes", "write_bytes":
                sc["llite:" + key] = sum_event("llite", key)
        def pr(key, val):
            print key.ljust(40, '.'), val
        pr("jobid", self.id)
        pr("begin", time.ctime(self.begin))
        pr("end", time.ctime(self.end))
        d0 = datetime.datetime.fromtimestamp(self.begin)
        d1 = datetime.datetime.fromtimestamp(self.end)
        pr("run_time", str(d1 - d0))
        pr("nr_hosts", len(self.hosts))
        # "nr_cores"
        for key, val in self.summary_cache.iteritems():
            pr(key, val)

# if __name__ == "main":
#     if len(sys.argv) == 0:
#         fatal("must specify a jobid\n")
