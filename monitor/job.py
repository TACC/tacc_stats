#!/usr/bin/env python
import errno, gzip, numpy, os, sge_acct, sys, time, urllib
# signal, string, subprocess

TS_IN_DIR = '/tmp/TS/in'
TS_OUT_DIR = '/tmp/TS/out'
TS_TMP_DIR = '/tmp/TS/tmp'
TS_VERBOSE = True # XXX

# mkdir -p /tmp/TS/{in,out,tmp}
# ln -s /scratch/projects/tacc_stats/archive /tmp/TS/in/stats
# ln -s /scratch/projects/tacc_stats/accounting /tmp/TS/in/accounting
# ln -s /scratch/projects/tacc_stats/hostfiles /tmp/TS/in/host_lists


IN_STATS_TIME_MAX = 86400 + 2 * 3600
IN_STATS_TIME_PAD = 1200

SF_SCHEMA_CHAR = '!'
SF_DEVICES_CHAR = '@'
SF_COMMENT_CHAR = '#'
SF_PROPERTY_CHAR = '$'
SF_MARK_CHAR = '%'

# stats/HOST/TIMESTAMP: raw stats files (in).
in_stats_dir = os.path.join(TS_IN_DIR, 'stats')

# sge_acct: mirror of sge accounting file or a chunk of it (in).
sge_acct_path = os.path.join(TS_IN_DIR, 'accounting')

# host_lists/JOBID: job host list (in).
host_list_dir = os.path.join(TS_IN_DIR, 'host_lists')

# DB TODO (out).

# job_stats_dir/JOBID: tar file per job (out).
out_stats_dir = os.path.join(TS_OUT_DIR, 'stats')


prog = os.path.basename(sys.argv[0])
if prog == "":
    prog = "***"


def trace(fmt, *args):
    if TS_VERBOSE:
        msg = fmt % args
        sys.stderr.write(prog + ": " + msg)


def error(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    

def fatal(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)
    sys.exit(1)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as (err, str):
        if err != errno.EEXIST:
            raise OSError(err, str)


def listdir_q(dir):
    try:
        return os.listdir(dir)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return []
        else:
            raise exc


def stats_file_discard_record(file):
    for line in file:
        if line.isspace():
            return


class Schema(object):
    __slots__ = ('entries', 'keys')

    def __init__(self, job, desc):
        # self.name = name
        # self.desc = desc
        self.entries = []
        self.keys = {}
        for i, s in enumerate(desc.split()):
            e = SchemaEntry(job, i, s)
            self.keys[e.key] = e
            self.entries.append(e)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               all(self.__getattribute__(attr) == other.__getattribute__(attr) for attr in self.__slots__)

    def __ne__(self, other):
        return not self.__eq__(other)

class SchemaEntry(object):
    __slots__ = ('key', 'index', 'is_control', 'is_event', 'width', 'mult', 'unit')

    def __init__(self, job, i, s):
        opt_lis = s.split(',')
        self.key = opt_lis[0]
        self.index = i
        self.is_control = False
        self.is_event = False
        self.width = None
        self.mult = None
        self.unit = None
        for opt in opt_lis[1:]:
            if len(opt) == 0:
                continue
            elif opt[0] == 'C':
                self.is_control = True
            elif opt[0] == 'E':
                self.is_event = True
            elif opt[0:2] == 'W=':
                self.width = int(opt[2:])
            elif opt[0:2] == 'U=':
                j = 2
                while j < len(opt) and opt[j].isdigit():
                    j += 1
                if j > 2:
                    self.mult = numpy.uint64(opt[2:j])
                if j < len(opt):
                    self.unit = opt[j:]
                if self.unit == "KB":
                    self.mult = numpy.uint64(1024)
                    self.unit = "B"
            else:
                # XXX
                job.error("unrecognized option `%s' in schema entry spec `%s'\n", opt, s)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               all(self.__getattribute__(attr) == other.__getattribute__(attr) for attr in self.__slots__)

    def __ne__(self, other):
        return not self.__eq__(other)


class Host(object):
    __slots__ = ('job', 'name', 'times', 'stats', 'marks')
    def __init__(self, job, name):
        # trace("job `%s', name `%s'\n", job.id, name)
        self.job = job
        self.name = name
        self.times = []
        self.stats = {}
        self.marks = {}

    def trace(self, fmt, *args):
        msg = fmt % args
        self.job.trace('%s: %s', self.name, msg)

    def error(self, fmt, *args):
        msg = fmt % args
        self.job.error('%s: %s', self.name, msg)

    def get_stats_paths(self):
        in_host_stats_dir = os.path.join(in_stats_dir, self.name)
        job_start = self.job.start_time - IN_STATS_TIME_PAD
        job_end = self.job.end_time + IN_STATS_TIME_PAD
        path_list = []
        try:
            for ent in os.listdir(in_host_stats_dir):
                base, dot, ext = ent.partition(".")
                if not base.isdigit():
                    continue
                # Prune to files that might overlap with job.
                ent_start = long(base)
                ent_end = ent_start + IN_STATS_TIME_MAX
                if max(job_start, ent_start) <= min(job_end, ent_end):
                    full_path = os.path.join(in_host_stats_dir, ent)
                    path_list.append((full_path, ent_start))
                    self.trace("path `%s', start %d\n", full_path, ent_start)
        except:
            pass
        path_list.sort(key=lambda tup: tup[1])
        return path_list

    def read_stats_file_header(self, file, start_time):
        schema = {}
        for line in file:
            try:
                c = line[0]
                if c == SF_SCHEMA_CHAR:
                    type_name, schema_desc = line[1:].split(None, 1)
                    schema[type_name] = Schema(self.job, schema_desc)
                elif c == SF_PROPERTY_CHAR:
                    pass
                elif c == SF_COMMENT_CHAR:
                    pass
                else:
                    break
            except Exception as exc:
                self.trace("file `%s', caught `%s' discarding line `%s'\n",
                           file.name, exc, line)
                break
        if self.job.schema:
            # Cheesy.
            if self.job.schema != schema:
                self.error("file `%s' schema mismatch\n", file.name)
                return None
        else:
            # We win!
            self.job.schema = schema
        return schema

    def parse_stats(self, file, schema, rec_time, line):
        type_name, dev_name, rest = line.split(None, 2)
        type_schema = schema.get(type_name)
        if not type_schema:
            self.trace("file `%s', unknown type `%s'\n", file.name, type_name)
            return
        type_stats = self.stats.setdefault(type_name, {})
        dev_file = type_stats.get(dev_name)
        if not dev_file:
            dev_file = self.job.open(type_name, self.name, dev_name, 'w',
                                     schema=type_schema)
            type_stats[dev_name] = dev_file
        # XXX dtype=numpy.uint64
        # XXX count=?
        vals = numpy.fromstring(rest, dtype=numpy.uint64, sep=' ')
        # if vals.shape != (len(schema.entries),):
        #     ...
        FS = ' '
        RS = '\n'
        dev_file.write(str(rec_time))
        dev_file.write(FS)
        vals.tofile(dev_file, sep=FS)
        dev_file.write(RS)

    def read_stats_file(self, file, start_time):
        schema = self.read_stats_file_header(file, start_time)
        if not schema:
            self.trace("file `%s' bad schema\n", file.name)
            return
        # Scan file for records belonging to JOBID.
        rec_time = start_time
        for line in file:
            try:
                c = line[0]
                if c.isdigit():
                    str_time, rec_jobid = line.split()
                    rec_time = long(str_time)
                    if rec_jobid == self.job.id:
                        self.trace("file `%s' rec_time %d, rec_jobid `%s'\n",
                                   file.name, rec_time, rec_jobid)
                        self.times.append(rec_time)
                        break
            except Exception as exc:
                self.trace("file `%s', caught `%s', discarding `%s'\n",
                           file.name, str(exc), line)
                stats_file_discard_record(file)
        else:
            # We got to the end of this file wthout finding any
            # records belonging to JOBID.  Try next path.
            self.trace("file `%s' has no records belonging to job\n", file.name)
            return
        # OK, we found a record belonging to JOBID.
        for line in file:
            try:
                c = line[0]
                if c.isdigit():
                    str_time, rec_jobid = line.split()
                    rec_time = long(str_time)
                    if rec_jobid != self.job.id:
                        return
                    self.trace("file `%s' rec_time %d, rec_jobid `%s'\n",
                               file.name, rec_time, rec_jobid)
                    self.times.append(rec_time)
                elif c.isalpha():
                    self.parse_stats(file, schema, rec_time, line)
                elif c == SF_MARK_CHAR:
                    mark = line[1:].strip()
                    self.marks[mark] = True
                elif c == SF_COMMENT_CHAR:
                    pass
                else:
                    pass #...
            except Exception as exc:
                self.trace("file `%s', caught `%s', discarding `%s'\n",
                           file.name, str(exc), line)
                stats_file_discard_record(file)

    def gather_stats(self):
        path_list = self.get_stats_paths()
        if len(path_list) == 0:
            self.error("no stats files overlapping job\n")
            return False
        for path, start_time in path_list:
            file = gzip.open(path) # XXX Gzip.
            self.read_stats_file(file, start_time)
        # Close all tmp files.
        for d in self.stats.itervalues():
            for f in d.itervalues():
                f.close()
#         begin_mark = 'begin %s' % self.job.id # No '%'.
#         if not begin_mark in self.marks:
#             self.error("no begin mark found\n")
#             return False
#         end_mark = 'end %s' % self.job.id # No '%'.
#         if not end_mark in self.marks:
#             self.error("no end mark found\n")
#             return False
        return True


def path_quote(str):
    return urllib.quote(str, safe='')


def path_unquote(str):
    return urllib.unquote(str)


class Job(object):
    # TODO errors/comments
    __slots__ = ('id', 'start_time', 'end_time', 'acct', 'schema', 'hosts', 'times', 'tmp_dir')

    def __init__(self, acct):
        self.id = acct['id']
        self.start_time = acct['start_time']
        self.end_time = acct['end_time']
        self.acct = acct
        self.schema = {}
        self.hosts = {}
        self.times = []
        self.tmp_dir = None

    def trace(self, fmt, *args):
        msg = fmt % args
        trace('%s: %s', self.id, msg)

    def error(self, fmt, *args):
        msg = fmt % args
        error('%s: %s', self.id, msg)

    def open(self, type_name, host_name, dev_name, mode='r', schema=None):
        type_ent = path_quote(type_name)
        host_ent = path_quote(host_name)
        dev_ent = path_quote(dev_name)
        dir = os.path.join(self.tmp_dir, type_ent, host_ent) # XXX Policy.
        if mode[0] == 'a' or mode[0] == 'w':
            mkdir_p(dir)
        path = os.path.join(dir, dev_ent)
        return open(path, mode)

    def iter_files(self, type_name, host_names=None, dev_names=None, mode='r'):
        type_ent = path_quote(type_name)
        type_dir = os.path.join(self.tmp_dir, type_ent)
        if host_names == None:
            host_ent_list = list(listdir_q(type_dir))
        else:
            host_ent_list = map(path_quote, host_names)
        for host_ent in host_ent_list:
            host_dir = os.path.join(type_dir, host_ent)
            if dev_names == None:
                dev_ent_list = list(listdir_q(host_dir))
            else:
                dev_ent_list = map(path_quote, dev_names)
            for dev_ent in dev_ent_list:
                yield (path_unquote(host_ent),
                       path_unquote(dev_ent),
                       open(os.path.join(host_dir, dev_ent), mode))

    def gather_stats(self):
        host_list_path = os.path.join(host_list_dir, self.id)
        try:
            host_list_file = open(host_list_path, 'r')
            host_list = [host for line in host_list_file for host in line.split()]
        except IOError as (err, str):
            self.error("cannot open host list `%s': %s\n", host_list_path, str)
            return False
        if len(host_list) == 0:
            self.error("empty host list\n")
            return False
        tmp_dir = os.path.join(TS_TMP_DIR, self.id)
        os.mkdir(tmp_dir)
        self.tmp_dir = tmp_dir
        for host_name in host_list:
            host = Host(self, host_name)
            if host.gather_stats():
                self.hosts[host_name] = host
            else:
                pass # FIXME
        if len(self.hosts) == 0:
            self.error("no good hosts\n")
            return False
        return True

    def set_times(self):
        # Ensure that times is sane and monotonically increasing.
        times_lis = [host.times for host in self.hosts.itervalues()]
        times_lis.sort(key=lambda lis: len(lis))
        times = list(times_lis[len(times_lis) / 2])
        times.sort()
        t_min = self.start_time
        for i in range(0, len(times)): 
            t = max(times[i], t_min)
            times[i] = t
            t_min = t + 1
        self.trace("nr times min %d, mid %d, max %d\n",
                   len(times_lis[0]), len(times), len(times_lis[-1]))
        self.trace("job start to first collect %d\n", times[0] - self.start_time)
        self.trace("last collect to job end %d\n", self.end_time - times[-1])
        self.times = times

    def process_stats_file(self, schema, in_file, out_file):
        A = numpy.loadtxt(in_file, dtype=numpy.uint64)
        m, n = A.shape
        if n != len(schema.entries) + 1:
            self.error("file `%s' has %d columns, expected %d\n",
                       n, len(schema.entries) + 1)
            return False
        P = numpy.array(A[0], dtype=numpy.uint64) # Prev.
        R = numpy.array(A[0], dtype=numpy.uint64) # Roll.
        B = numpy.zeros((len(self.times), n), dtype=numpy.uint64) # Output.
        for k, t in enumerate(self.times):
            B[k, 0] = t
            # Choose i so that A[i, 0] is as close to t as possible.
            # This should be improved to avoid binary search.
            i = numpy.searchsorted(A[:, 0], t)
            # If 0 < i < m then A[i - 1, 0] <= t <= A[i, 0].
            if i == 0:
                pass
            elif i < m:
                if t - A[i - 1, 0] < A[i, 0] - t:
                    i = i - 1
            else:
                i = m - 1
            for j, e in enumerate(schema.entries, start=1): # + 1.
                v = A[i, j]
                if e.is_event:
                    # Check for rollover.
                    if v < P[j]:
                        if e.width:
                            self.trace("file `%s' time %d, counter `%s', rollover prev %d, val %d\n",
                                       in_file.name, A[i, 0], e.key, P[j], v)
                            R[j] -= numpy.uint64(1L << e.width)
                        elif v == 0:
                            self.trace("file `%s' time %d, counter `%s', rollover prev %d, val %d\n",
                                       in_file.name, A[i, 0], e.key, P[j], v)
                            v = P[j] # Ugh.
                        else:
                            self.error("file `%s' time %d, counter `%s', rollover prev %d, val %d\n",
                                       in_file.name, A[i, 0], e.key, P[j], v)
                            # return False
                    v -= R[j]
                if e.mult:
                    v *= e.mult
                B[k, j] = v
            P = A[i, :]
        # header=, footer=
        numpy.savetxt(out_file, B, fmt='%u')
        return True

    def process_stats(self):
        for type_name, type_schema in self.schema.iteritems():
            for host_name, dev_name, in_file in self.iter_files(type_name):
                out_file = open(in_file.name + '~', 'w') # XXX.
                if self.process_stats_file(type_schema, in_file, out_file):
                    os.rename(out_file.name, in_file.name)
                else:
                    os.unlink(in_file.name)
                    os.unlink(out_file.name)
                in_file.close()
                out_file.close()

#if False:
#     start_time = time.time() - 2 * 86400
#     end_time = start_time + 86400
#
#     sge_acct_file = open(sge_acct_path, 'r')
#     for acct in sge_acct.reader(sge_acct_file, start_time=start_time, end_time=end_time):
#        (acct)

# acct_file = open('accounting', 'r')
# acct_lis = [a for a in sge_acct.reader(acct_file)]
# # acct = acct_lis[0]
# acct = filter(lambda acct: acct['id'] == "2255593", acct_lis)[0]

# job = Job(acct)
# job.gather_stats()
# job.set_times()
# job.process_stats()

