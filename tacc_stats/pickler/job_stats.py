#!/usr/bin/env python
import datetime, errno, glob, numpy, os, sys, time, gzip
from tacc_stats.pickler import amd64_pmc, intel_process
import re
import string

verbose = os.getenv('TACC_STATS_VERBOSE')

if not verbose:
    numpy.seterr(over='ignore')

prog = os.path.basename(sys.argv[0])
if prog == "":
    prog = "***"

def trace(fmt, *args):
    if verbose:
        msg = fmt % args
        sys.stderr.write(prog + ": " + msg)

def error(fmt, *args):
    msg = fmt % args
    sys.stderr.write(prog + ": " + msg)

RAW_STATS_TIME_MAX = 86400 + 2 * 3600
RAW_STATS_TIME_PAD = 1200

SF_SCHEMA_CHAR = '!'
SF_DEVICES_CHAR = '@'
SF_COMMENT_CHAR = '#'
SF_PROPERTY_CHAR = '$'
SF_MARK_CHAR = '%'

KEEP_EDITS = False

def schema_fixup(type_name, desc):
    """ This function implements a workaround for a known issue with incorrect schema """
    """ definitions for irq, block and sched tacc_stats metrics. """

    if type_name == "ib" and 'W=32' not in desc:
        # All of the irq metrics are 32 bits wide
        res = ""
        for token in desc.split():
            res += token.strip() + ",W=32 "
        return res.strip()+'\n'


    if type_name == "irq":
        # All of the irq metrics are 32 bits wide
        res = ""
        for token in desc.split():
            res += token.strip() + ",W=32 "
        return res

    elif type_name == "sched":
        # Most sched counters are 32 bits wide with 3 exceptions
        res = ""
        sixtyfourbitcounters = [ "running_time,E,U=ms", "waiting_time,E,U=ms", "pcount,E" ]
        for token in desc.split():
            if token in sixtyfourbitcounters:
                res += token.strip() + " "
            else:
                res += token.strip() + ",W=32 "
        return res
    elif type_name == "block":
        # Most block counters are 64bits wide with a few exceptions
        res = ""
        thirtytwobitcounters = [ "rd_ticks,E,U=ms", "wr_ticks,E,U=ms", "in_flight", "io_ticks,E,U=ms", "time_in_queue,E,U=ms" ]
        for token in desc.split():
            if token in thirtytwobitcounters:
                res += token.strip() + ",W=32 "
            else:
                res += token.strip() + " "
        return res
    elif type_name == "panfs":
        # The syscall_*_(n+)s stats are not events
        res = ""
        for token in desc.split():
            token = token.strip()
            if token.startswith("syscall_") and ( token.endswith("_s,E,U=s") or token.endswith("_ns,E,U=ns")):
                res += string.replace(token, "E,", "") + " "
            else:
                res += token + " "
        return res

    return desc

class SchemaEntry(object):
    __slots__ = ('key', 'index', 'is_control', 'is_event', 'width', 'mult', 'unit')

    def __init__(self, i, s):
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
                raise ValueError("unrecognized option `%s' in schema entry spec `%s'\n", opt, s)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               all(self.__getattribute__(attr) == other.__getattribute__(attr) \
                   for attr in self.__slots__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        lis = [] # 'index=%d' % self.index
        if self.is_event:
            lis.append('is_event=True')
        elif self.is_control:
            lis.append('is_control=True')
        if self.width:
            lis.append('width=%d' % int(self.width))
        if self.mult:
            lis.append('mult=%d' % int(self.mult))
        if self.unit:
            lis.append('unit=%s' % self.unit)
        return '(' + ', '.join(lis) + ')'


class Schema(dict):
    def __init__(self, desc):
        dict.__init__(self)
        self.desc = desc
        self._key_list = []
        self._value_list = []
        for i, s in enumerate(desc.split()):
            e = SchemaEntry(i, s)
            dict.__setitem__(self, e.key, e)
            self._key_list.append(e.key)
            self._value_list.append(e)

    def __iter__(self):
        return self._key_list.__iter__()

    def __repr__(self):
        return '{' + ', '.join(("'%s': %s" % (k, repr(self[k]))) \
                               for k in self._key_list) + '}'

    def _notsup(self, s):
        raise TypeError("'Schema' object does not support %s" % s)

    def __delitem__(self, k, v):
        self._notsup('item deletion')

    def pop(self, k, d=None):
        self._notsup('removal')

    def popitem(self):
        self._notsup('removal')

    def setdefault(self, k, d=None):
        self._notsup("item assignment")

    def update(self, **args):
        self._notsup("update")

    def items(self):
        return zip(self._key_list, self._value_list)

    def iteritems(self):
        for k in self._key_list:
            yield (k, dict.__getitem__(self, k))

    def iterkeys(self):
        return self._key_list.__iter__()

    def itervalues(self):
        return self._value_list.__iter__()

    def keys(self):
        return self._key_list

    def values(self):
        return self._value_list


def stats_file_discard_record(file):
    for line in file:
        if line.isspace():
            return


class Host(object):
    #__slots__ = ('job', 'name', 'name_ext', 'times', 'marks', 'raw_stats', 'raw_stats_dir', 'stats')

    def __init__(self, job, name, raw_stats_dir, name_ext = ''):
        self.job = job
        self.name = name
        self.name_ext = name_ext
        self.times = []
        self.marks = {}
        self.raw_stats = {}
        self.raw_stats_dir = raw_stats_dir

    def trace(self, fmt, *args):
        self.job.trace('%s: ' + fmt, self.name, *args)

    def error(self, fmt, *args):
        self.job.error('%s: ' + fmt, self.name, *args)

    def get_stats_paths(self):
        raw_host_stats_dir = os.path.join(self.raw_stats_dir, self.name + self.name_ext)
        job_start = self.job.start_time - RAW_STATS_TIME_PAD
        job_end = self.job.end_time + RAW_STATS_TIME_PAD
        path_list = []
        try:
            for ent in os.listdir(raw_host_stats_dir):
                base, dot, ext = ent.partition(".")
                if not base.isdigit():
                    continue
                # Support for filenames of the form %Y%m%d
                if re.match('^[0-9]{4}[0-1][0-9][0-3][0-9]$', base):
                    base = (datetime.datetime.strptime(base,"%Y%m%d") - datetime.datetime(1970,1,1)).total_seconds()
                # Prune to files that might overlap with job.
                ent_start = int(base) - 3*RAW_STATS_TIME_MAX
                ent_end   = int(base) + 2*RAW_STATS_TIME_MAX

                if (max(job_start, ent_start) <= min(job_end, ent_end)):
                    full_path = os.path.join(raw_host_stats_dir, ent)
                    path_list.append((full_path, ent_start))
                    self.trace("path `%s', start %d\n", full_path, ent_start)
        except Exception as e:
            print(e)
            pass
        path_list.sort(key=lambda tup: tup[1])
        return path_list

    def read_stats_file_header(self, lines):
        file_schemas = {}

        for line in lines:
            try:
                c = line[0]
                if c == SF_SCHEMA_CHAR:
                    type_name, schema_desc = line[1:].split(None, 1)
                    schema = self.job.get_schema(type_name, schema_desc)
                    if schema:
                        file_schemas[type_name] = schema
                    else:
                        self.error("type `%s', schema mismatch desc\n%s\n",
                                   type_name, schema_desc)
                elif c == SF_PROPERTY_CHAR:
                    pass
                elif c == SF_COMMENT_CHAR:
                    pass
                else:
                    break
            except Exception as exc:
                self.trace("caught `%s' discarding line `%s'\n",
                           exc, line)
                break
        return file_schemas

    def parse_stats(self, rec_time, line, file_schemas, fd):
        try:
            type_name, dev_name, rest = line.split(None, 2)
        except: return
        schema = file_schemas.get(type_name)
        if not schema:
            self.error("file `%s', unknown type `%s', discarding line `%s'\n",
                       fd.name, type_name, line)
            return
        # TODO stats_dtype = numpy.uint64
        # XXX count = ?
        try:
            vals = numpy.fromstring(rest, dtype=numpy.uint64, sep=' ')
        except: 
            return
        if vals.shape[0] != len(schema):
            self.error("file `%s', type `%s', expected %d values, read %d, discarding line `%s'\n",
                       fd.name, type_name, len(schema), vals.shape[0], line)
            return
        type_stats = self.raw_stats.setdefault(type_name, {})
        dev_stats = type_stats.setdefault(dev_name, [])
        dev_stats.append((rec_time, vals))

    def read_stats_file(self, fd):
        lines = fd.readlines()
        begin_idx = None
        for line in lines:    
            if line[0].isdigit():
                str_time, str_jobid, str_hostname = line.split()
                if str(self.job.id) in set(str_jobid.split(',')):
                    begin_idx = lines.index(line)
                    break

        if not begin_idx: 
            return

        file_schemas = self.read_stats_file_header(lines)
        if not file_schemas:
            self.trace("file `%s' bad header\n", fd.name)
            return

        record = False
        for line in lines[begin_idx:]:            
            if line[0].isdigit():
                str_time,str_jobids,hostname = line.split()
                if str(self.job.id) in set(str_jobids.split(',')):
                    self.times += [float(str_time)]
                    record = True
                else:
                    record = False
            elif record and line[0].isalpha():
                self.parse_stats(float(str_time), line, file_schemas, fd)                            
            elif line.startswith("%begin") or line.startswith("%end"):
                str_jobid = line.split()[1]
                if str(self.job.id) == str_jobid:
                    self.marks[line[1:].strip()] = True
                    record = True
                else:
                    record = False

    def gather_stats(self):
        path_list = self.get_stats_paths()
        if len(path_list) == 0:
            self.error("no stats files overlapping job\n")
            return False

        # read_stats_file() and parse_stats() append stats records
        # into lists of tuples in self.raw_stats.  The lists will be
        # converted into numpy arrays below.
        for path, start_time in path_list:
            #try:
            #    with gzip.open(path, "r") as fd:
            #        self.read_stats_file(fd)
            #except IOError as ioe:
            try:
                with open(path, "r") as fd:
                    self.read_stats_file(fd)
            except:
                self.error("read error for file %s\n", path)
                
        begin_mark = 'begin %s' % self.job.id # No '%'.
        if not begin_mark in self.marks:
            self.error("no begin mark found\n")
            return False
        end_mark = 'end %s' % self.job.id # No '%'.
        if not end_mark in self.marks:
            self.error("no end mark found\n")
            return False

        return self.raw_stats

    def get_stats(self, type_name, dev_name, key_name):
        """Host.get_stats(type_name, dev_name, key_name)
        Return the vector of stats for the given type, dev, and key.
        """
        schema = self.job.get_schema(type_name)
        index = schema[key_name].index
        return self.stats[type_name][dev_name][:, index]


class Job(object):
    # TODO errors/comments
    __slots__ = ('id', 'start_time', 'end_time', 'acct', 'schemas', 'hosts',
                 'times','stats_home', 'host_list_dir', 'host_name_ext', 'edit_flags', 'errors', 'overflows', 'batch_acct')

    def __init__(self, acct, stats_home, host_list_dir, host_name_ext):
        self.id = acct['id']
        self.start_time = acct['start_time']
        self.end_time = acct['end_time']
        self.acct = acct
        self.schemas = {}
        self.hosts = {}
        self.times = []
        self.stats_home = stats_home
        self.host_name_ext = '.' + host_name_ext
        self.host_list_dir = host_list_dir
        self.edit_flags = []
        self.errors = set()
        self.overflows = dict()

    def trace(self, fmt, *args):
        trace('%s: ' + fmt, self.id, *args)

    def error(self, fmt, *args):
        error('%s: ' + fmt, self.id, *args)

    def get_schema(self, type_name, desc=None):
        schema = self.schemas.get(type_name)
        if schema:
            if desc and schema.desc != schema_fixup(type_name,desc):
                # ...
                return None
        elif desc:
            desc = schema_fixup(type_name, desc)
            schema = self.schemas[type_name] = Schema(desc)
        return schema

    def get_host_list_path(self,acct,host_list_dir):
        """Return the path of the host list written during the prolog."""
        start_date = datetime.date.fromtimestamp(acct['start_time'])
        base_glob = 'hostlist.' + acct['id']
        for days in (0, -1, 1, -2, 2, -3, 3):
            yyyy_mm_dd = (start_date + datetime.timedelta(days)).strftime("%Y/%m/%d")
            full_glob = os.path.join(host_list_dir, yyyy_mm_dd, base_glob)

            for path in glob.iglob(full_glob):
                return path
        return None

    def gather_stats(self):
        if "host_list" in self.acct:
            host_list = self.acct['host_list']
        else:
            path = self.get_host_list_path(self.acct, self.host_list_dir)
            if not path:
                self.error("no host list found\n")
                return False
            try:
                with open(path, "rb") as file:
                    host_list = [host for line in file for host in line.split()]
            except OSError as e:
                self.error("cannot open host list `%s': %s\n", path, e)
                return False
        if len(host_list) == 0:
            self.error("empty host list\n")
            return False

        # Try this out
        if self.acct['nodes'] != len(host_list): return False

        for host_name in host_list:
            # TODO Keep bad_hosts.
            try: host_name = host_name.split('.')[0]
            except: pass
            try:
                host = Host(self, host_name, self.stats_home, self.host_name_ext)
            except:
                host = Host(self, host_name, self.stats_home)
            if host.gather_stats():
                self.hosts[host_name] = host
            else: pass

        if not self.hosts:
            self.error("no good hosts\n")
            return False
        return True

    def munge_times(self):

        times_lis = []

        for host in self.hosts.values():
            times_lis.append(host.times)
            del host.times

        times_lis.sort(key=lambda lis: len(lis))
        # Choose times to have median length.
        times = list(times_lis[len(times_lis) // 2])
        if not times:
            return False
        times.sort()
        # Ensure that times is sane and monotonically increasing.
        t_min = 0
        for i in range(0, len(times)): 
            t = max(times[i], t_min)
            times[i] = t
            t_min = t + 1
        self.trace("nr times min %d, mid %d, max %d\n",
                   len(times_lis[0]), len(times), len(times_lis[-1]))
        self.trace("job start to first collect %d\n", times[0] - self.start_time)
        self.trace("last collect to job end %d\n", self.end_time - times[-1])
        self.times = numpy.array(times, dtype=numpy.uint64)
        #if len(times_lis[0]) != len(times_lis[-1]):
        #    self.errors.add( "Number of records differs between hosts (min {}, max {})".format(len(times_lis[0]), len(times_lis[-1]) ) )
        return True
    
    def process_dev_stats(self, host, type_name, schema, dev_name, raw):
        def trace(fmt, *args):
            return self.trace("host `%s', type `%s', dev `%s': " + fmt,
                              host.name, type_name, dev_name, *args)
        def error(fmt, *args):
            return self.error("host `%s', type `%s', dev `%s': " + fmt,
                              host.name, type_name, dev_name, *args)
        # raw is a list of pairs with car the timestamp and cdr a 1d
        # numpy array of values.
        m = len(self.times)
        n = len(schema)
        try:
            A = numpy.zeros((m, n), dtype=numpy.uint64) # Output.
        except MemoryError as e:
            error("cannot allocate A %s\n", e)
            return None
        # First and last of A are first and last from raw.
        A[0] = raw[0][1]
        A[m - 1] = raw[-1][1]
        k = 0
        # len(raw) may not be equal to m, so we fill out A by choosing values
        # with the closest timestamps.
        # TODO sort out host times
        host.times = []
        for i in range(1, m-1):
            t = self.times[i]
            while k + 1 < len(raw) and abs(raw[k + 1][0] - t) <= abs(raw[k][0] - t):
                k += 1
            #jitter = abs(raw[k][0] - t)
            #if jitter > 60:
            #    self.errors.add("Warning - high jitter for host {} job {} Actual time {}, Thunked to {} (Delta {})".format(host.name, self.id, raw[k][0], t, jitter))
            A[i] = raw[k][1]
            host.times.append(raw[k][0])

        # OK, we fit the raw values into A.  Now fixup rollover and
        # convert units.
        for e in schema.values():
            j = e.index
            if e.is_event:
                p = r = A[0, j] # Previous raw, rollover/baseline.
                # Rebase, check for rollover.
                for i in range(0, m):
                    v = A[i, j]
                    if v < p:
                        # Looks like rollover.
                        # Rebase narrow counters and spurious resets.
                        # 64-bit overflows are correctly handled automatically                        
                        fudged = False
                        #if 'intel_' in type_name: 
                        #    r = numpy.uint(0) - A[i-1,j]
                        if e.width:
                            trace("time %d, counter `%s', rollover prev %d, curr %d\n",
                                  self.times[i], e.key, p, v)
                            a = 1.0
                            if type_name == 'intel_rapl':
                                a = 0.06104
                            r -= numpy.uint64(1 << e.width)*a

                        elif v == 0 or (type_name == 'ib_ext' or type_name == 'ib_sw') or \
                                (type_name == 'cpu' and e.key == 'iowait'):
                            # We will assume a spurious reset, 
                            # and the reset happened at the start of the counting period.
                            # This happens with IB counters and sometimes with Lustre stats.
                            # A[i,j] = v + A[i-1,j] = v - r. Rebase to previous value.
                            r = numpy.uint(0) - A[i-1,j]

                            if KEEP_EDITS:
                                self.edit_flags.append("(time %d, host `%s', type `%s', dev `%s', key `%s')" %
                                                       (self.times[i],host.name,type_name,dev_name,e.key))
                            fudged =True
                        # These logs conflict with a years worth of data
                        """
                        if type_name not in ['ib', 'ib_ext'] and not fudged:
                            width = e.width if e.width else 64
                            if ( v - p ) % (2**width) > 2**(width-1):
                                # This counter rolled more than half of its range
                                self.logoverflow(host.name, type_name, dev_name, e.key)
                        """
                    A[i, j] = v - r
                    p = v
            if e.mult:
                for i in range(0, m):
                    A[i, j] *= e.mult
            if "MSR_DRAM_ENERGY_STATUS" == schema.keys()[j]: 
                for i in range(0, m):
                    A[i, j] *= 0.0153/0.06104

        return A

    def logoverflow(self, host_name, type_name, dev_name, key_name):
        if type_name not in self.overflows:
            self.overflows[type_name] = dict()
        if dev_name not in self.overflows[type_name]:
            self.overflows[type_name][dev_name] = dict()
        if key_name not in self.overflows[type_name][dev_name]:
            self.overflows[type_name][dev_name][key_name] = []

        self.overflows[type_name][dev_name][key_name].append(host_name)

    def process_stats(self):
        for host in self.hosts.values():
            host.stats = {}
            for type_name, raw_type_stats in host.raw_stats.items():
                stats = host.stats[type_name] = {}
                schema = self.schemas[type_name]
                for dev_name, raw_dev_stats in raw_type_stats.items():
                    try:
                        stats[dev_name] = self.process_dev_stats(host, type_name, schema,
                                                                 dev_name, raw_dev_stats)
                    except:
                        continue
            del host.raw_stats
        amd64_pmc.process_job(self)
        intel_process.process_job(self)
        # Clear mult, width from schemas. XXX
        for schema in self.schemas.values():
            for e in schema.itervalues():
                e.width = None
                e.mult = None
        return True
    
    def aggregate_stats(self, type_name, host_names=None, dev_names=None):
        """Job.aggregate_stats(type_name, host_names=None, dev_names=None)
        """
        # TODO Handle control registers.
        schema = self.schemas[type_name]

        m = len(self.times)
        n = len(schema.keys())
        A = numpy.zeros((m, n), dtype=numpy.uint64) # Output.       
        nr_hosts = 0
        nr_devs = 0
        if host_names:
            host_list = [self.hosts[name] for name in host_names]
        else:
            host_list = self.hosts.values()
        for host in host_list:
            type_stats = host.stats.get(type_name)
            if not type_stats:
                continue
            nr_hosts += 1
            if dev_names:
                dev_list = [type_stats[name] for name in dev_names]
            else:
                dev_list = type_stats.values()
            for dev_stats in dev_list:
                A += dev_stats
                nr_devs += 1
        return (A, nr_hosts, nr_devs)

    def get_stats(self, type_name, dev_name, key_name):
        """Job.get_stats(type_name, dev_name, key_name)
        Return a dictionary with keys host names and values the vector
        of stats for the given type, dev, and key.
        """
        schema = self.get_schema(type_name)
        index = schema[key_name].index
        host_stats = {}
        for host_name, host in self.hosts.items():
            host_stats[host_name] = host.stats[type_name][dev_name][:, index]
        return host_stats


def from_acct(acct, stats_home, host_list_dir, host_name_ext):
    """from_acct(acct, stats_home)
    Return a Job object constructed from the appropriate accounting data acct using
    stats_home as the base directory, running all required processing.
    """
    job = Job(acct, stats_home, host_list_dir, host_name_ext)

    if job.gather_stats() and job.munge_times() and job.process_stats():
        return job
    else:
        return False
    

