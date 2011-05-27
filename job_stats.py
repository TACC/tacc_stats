#!/opt/apps/python/2.7.1/bin/python
import argparse, glob, gzip, os, signal, string, subprocess, sys, time


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

job_times_cmd = "./job_times" # XXX
hostfile_dir = "/share/sge6.2/default/tacc/hostfile_logs"
archive_dir = "/scratch/projects/tacc_stats/archive"

STATS_PROGRAM = "tacc_stats" # XXX
STATS_VERSION = "1.0.1" # XXX
FILE_TIME_MAX = 86400 + 3600 # XXX
SF_SCHEMA_CHAR = '!'
SF_DEVICES_CHAR = '@'
SF_COMMENT_CHAR = '#'
SF_PROPERTY_CHAR = '$'
SF_MARK_CHAR = '%'

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
                    if ent.width:
                        trace("rollover on type `%s', dev `%s', counter `%s'\n'", name, dev, ent.key)
                        dh[0][i] -= 1L << ent.width
                    else:
                        # XXX Need context.
                        error("full width rollover on type `%s, dev `%s', counter `%s'\n", name, dev, ent.key)
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
        #
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
        self.local_begin = None
        self.local_end = None
        self.hosts = []
        # Get begin and end time.
        times_proc = subprocess.Popen([job_times_cmd, self.id], stdout=subprocess.PIPE)
        times_proc_out, times_proc_err = times_proc.communicate()
        try:
            self.begin, self.end = map(long, times_proc_out.split())
        except ValueError: # Terrible.
            error("cannot get begin, end times for job `%s'\n", self.id)
            return
        trace("jobid `%s', begin %d, end %d\n", self.id, self.begin, self.end)
        self.local_begin = time.localtime(self.begin)
        self.local_end = time.localtime(self.end)
        # Find the hostfile written during the prolog.  For example:
        # /share/sge6.2/default/tacc/hostfile_logs/2011/05/19/prolog_hostfile.1957000.IV32627
        # TODO Try day before or after on failure.
        # TODO Move hostfile search to job_times callback.
        hostfile = None
        yyyy_mm_dd = time.strftime("%Y/%m/%d", self.local_begin)
        hostfile_glob = "%s/%s/prolog_hostfile.%s.*" % (hostfile_dir, yyyy_mm_dd, self.id)
        for file in glob.glob(hostfile_glob):
            if os.access(file, os.R_OK):
                hostfile = file
                break
        if hostfile:
            for host in open(hostfile, "r"):
                host = host.strip()
                if len(host) != 0:
                    self.hosts.append(JobHost(self, host))
        else:
            # Throw?  Blech.
            error("no hostfile for job `%s'\n", self.id)


# signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# opt_parser = argparse.ArgumentParser(description="Collect job stats.", prog=prog)
# opt_parser.add_argument("--emit-stats", dest="emit_stats", action="store_true", default=False)
# opt_parser.add_argument("-o", "--out-dir", dest="out_dir", default=None)
# opt_parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
# # opt_parser.add_argument("-b", "--begin", dest="begin")
# # opt_parser.add_argument("-e", "--end", dest="end")
# # opt_parser.add_argument("-h", "--hostfile", dest="hostfile")
# # opt_parser.add_argument("-j", "--jobid", dest="jobid")
# # opt_parser.add_argument("-f", "--fqdn", "--full-hostname", action="store_true", dest="fqdn")
# # opt_parser.add_argument("-m", "--marks", action="store_true", dest="marks")
# # opt_parser.add_argument("-t", "--time-fmt", metavar="FMT", dest="time_fmt", default="%b %d %H:%M:%S")

# # prefix time,host,jobid,type,dev
# # fs, rs
# # size_format

# (opt, args) = opt_parser.parse_known_args()

# if len(args) == 0:
#     fatal("must specify a jobid\n")
# jobid = args[0]
# opt.out_dir = opt.out_dir or "%s.%s" % (jobid, prog)

# trace("args `%s'\n", args)
# trace("opt `%s'\n", opt)
# trace("jobid `%s'\n", jobid)

# times_proc = subprocess.Popen([job_times_cmd, jobid], stdout=subprocess.PIPE)
# times_proc_out, times_proc_err = times_proc.communicate()
# job_begin, job_end = map(long, times_proc_out.split()) # catch ValueError

# trace("job_begin `%d'\n", job_begin)
# trace("job_end `%d'\n", job_end)

# # Find the hostfile written during the prolog.  For example:
# # /share/sge6.2/default/tacc/hostfile_logs/2011/05/19/prolog_hostfile.1957000.IV32627

# # TODO Try day before or after on failure.
# # TODO Move hostfile search to job_times callback.

# yyyy_mm_dd = time.strftime("%Y/%m/%d", time.localtime(job_begin))
# hostfile_glob = "%s/%s/prolog_hostfile.%s.*" % (hostfile_dir, yyyy_mm_dd, jobid)
# for hostfile in glob.glob(hostfile_glob):
#     job_hostfile = hostfile
#     break
# else:
#     fatal("no hostfile for job `%s'\n", jobid)

# trace("job_hostfile `%s'\n", job_hostfile)

# os.mkdir(opt.out_dir) # EEXIST?

# class Stats:
#     def __init__(self, ent_list, vals):
#         self.base = map(lambda e, v: v if e.event else 0L, ent_list, vals)
#         self.prev = list(self.base)
#         # ent.gauge
#         self.min = map(lambda e, v: 0L if e.event else v, ent_list, vals)
#         self.max = list(self.min)

# class StatsType:
#     def __init__(self, name, spec):
#         self.name = name
#         self.schema = Schema(spec)
#         self.dev_to_stats = {}
#         trace("name `%s', schema `%s'\n", self.name, self.schema)
#     #
#     def emit_schema(self, file):
#         file.write("%s%s %s\n" % (SF_SCHEMA_CHAR, self.name, self.schema.spec))
#     #
#     def emit_record(self, file, dev, vals):
#         if len(vals) != len(self.schema.ent_list):
#             error("record length mismatch for type `%s', dev `%s'\n", self.name, self.dev)
#             return
#         out_vals = list(vals)
#         stats = self.dev_to_stats.get(dev)
#         if not stats:
#             self.dev_to_stats[dev] = stats = Stats(self.schema.ent_list, vals)
#         for ent in self.schema.ent_list:
#             i = ent.index
#             if ent.control:
#                 pass
#             elif ent.event:
#                 # Check for rollover.
#                 if vals[i] < stats.prev[i]:
#                     if ent.width:
#                         trace("rollover on type `%s', dev `%s', counter `%s'\n'", self.type, dev, ent.key)
#                         stats.base[i] -= 1L << ent.width
#                     else:
#                         # XXX Need context.
#                         error("full width rollover on type `%s, dev `%s', counter `%s'\n", self.type, dev, ent.key)
#                 out_vals[i] -= stats.base[i]
#                 stats.prev[i] = vals[i]
#             else: # ent.gauge
#                 stats.min[i] = min(stats.min[i], vals[i])
#                 stats.max[i] = max(stats.max[i], vals[i])
#         file.write("%s %s %s\n" % (self.name, dev, string.join(map(str, out_vals))))
#     #
#     def emit_stats(self, file):
#         type_sum = len(self.schema.ent_list) * [ 0L ]
#         for dev, stats in self.dev_to_stats.iteritems():
#             for ent in self.schema.ent_list:
#                 i = ent.index
#                 if ent.control:
#                     pass
#                 elif ent.event:
#                     type_sum[i] += stats.prev[i] - stats.base[i]
#                 else: # ent.gauge
#                     dev_min = stats.min[i]
#                     dev_max = stats.max[i]
#                     file.write("%s%s %s %s min %d max %d\n" % (SF_COMMENT_CHAR, self.name, dev, ent.key, dev_min, dev_max))
#         for ent in self.schema.ent_list:
#             i = ent.index
#             file.write("%s%s %s sum %d\n" % (SF_COMMENT_CHAR, self.name, ent.key, type_sum[i]))

# class StatsFile:
#     def __init__(self, file):
#         self.file = file
#         self.time = 0
#         self.jobid = "0"
#         self.type_dict = {}
#         self.prop_dict = {}
#         self.empty = True
#     #
#     def set_schema(self, name, spec):
#         st = self.type_dict.get(name)
#         if st:
#             # TODO Check that old and new schemas agree.
#             pass
#         else:
#             self.type_dict[name] = StatsType(name, spec)
#     #
#     def begin_group(self, time, jobid):
#         self.time = time
#         self.jobid = time
#         if self.empty:
#             self.emit_header()
#         self.file.write("\n%d %s\n" % (time, jobid))
#     #
#     def emit_header(self):
#         self.file.write("%s%s %s\n" % (SF_COMMENT_CHAR, STATS_PROGRAM, STATS_VERSION))
#         for key, val in self.prop_dict.iteritems():
#             self.file.write("%s%s %s\n" % (SF_PROPERTY_CHAR, key, val))
#         for st in self.type_dict.itervalues():
#             st.emit_schema(self.file)
#         self.empty = False
#     #
#     def emit_mark(self, mark):
#         self.file.write("%s%s\n" % (SF_MARK_CHAR, mark))
#     #
#     def emit_record(self, name, dev, vals):
#         st = self.type_dict.get(name)
#         if st:
#             st.emit_record(self.file, dev, vals)
#         else:
#             error("stats file `%s' contains unknown type `%s'\n", self.file.name, name)
#     #
#     def close(self):
#         if opt.emit_stats:
#             for st in self.type_dict.itervalues():
#                 st.emit_stats(self.file)
#         self.file.close()

# for host in open(job_hostfile, "r"):
#     host = host.strip()
#     if len(host) == 0:
#         continue
#     host_dir = os.path.join(archive_dir, host)
#     trace("host `%s', host_dir `%s'\n", host, host_dir)
#     host_file_info = []
#     for path in os.listdir(host_dir):
#         if path[0] == '.':
#             continue
#         file_name, file_ext = path.split('.')
#         # Prune to files that might overlap with job.
#         file_begin = long(file_name)
#         file_end_max = file_begin + FILE_TIME_MAX
#         if max(job_begin, file_begin) <= min(job_end, file_end_max):
#             full_path = os.path.join(host_dir, path)
#             host_file_info.append((file_begin, file_ext, full_path))
#     if len(host_file_info) == 0:
#         error("host `%s' has no stats files overlapping job `%s'\n", host, jobid)
#         continue
#     host_file_info.sort(key=lambda info: info[0])
#     trace("host_file_info `%s'\n", host_file_info)
#     out_path = os.path.join(opt.out_dir, host)
#     out_file = StatsFile(open(out_path, "w"))
#     #
#     begin_mark = end_mark = False
#     rec_time = 0
#     rec_jobid = ""
#     for info in host_file_info:
#         for line in gzip.open(info[2]):
#             c = line[0]
#             #
#             if c == SF_SCHEMA_CHAR:
#                 rec = line[1:].strip().split(" ", 1)
#                 out_file.set_schema(rec[0], rec[1])
#             #
#             elif c == SF_DEVICES_CHAR:
#                 pass # TODO
#             #
#             elif c == SF_COMMENT_CHAR:
#                 pass
#             #
#             elif c == SF_PROPERTY_CHAR:
#                 pass # TODO out_file.emit_property(line[1:))
#             #
#             elif c == SF_MARK_CHAR:
#                 mark = line[1:].strip()
#                 if mark == "begin %s" % jobid:
#                     begin_mark = True
#                 elif mark == "end %s" % jobid:
#                     end_mark = True
#                 if rec_jobid == jobid:
#                     out_file.emit_mark(mark)
#             #
#             elif c.isdigit():
#                 (str_time, rec_jobid) = line.split()
#                 rec_time = long(str_time)
#                 trace("rec_jobid `%s'\n", rec_jobid)
#                 if rec_jobid == jobid:
#                     out_file.begin_group(rec_time, rec_jobid)
#             #
#             elif c.isalpha():
#                 if rec_jobid == jobid:
#                     rec = line.split()
#                     out_file.emit_record(rec[0], rec[1], map(long, rec[2:]))
#             #
#     if not begin_mark:
#         error("no begin mark found for host `%s'\n", host)
#     if not end_mark:
#         error("no end mark found for host `%s'\n", host)
#     out_file.close()

