#!/opt/apps/python/2.7.1/bin/python
import job_stats, numpy, signal, string, sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def first_value(dict):
    for value in dict.itervalues():
        return value


class Report(object):
    def __init__(self, job):
        self.cols = []
        self.dict = {}
        self.add_info('id', job.id)
        self.add_info('owner', job.info['owner'])
        self.add_info('queue_time', job.begin - long(job.info['submission_time']))
        self.add_info('run_time', job.end - job.begin)
        self.add_info('nr_hosts', len(job.hosts))
        self.add_info('nr_slots', long(job.info['slots']))
        self.add_info('pe', job.info['granted_pe'])
        self.add_events(job, 'amd64_core', keys=['USER', 'DCSF', 'SSE_FLOPS'])
        self.add_events(job, 'amd64_sock', keys=['DRAM', 'HT0', 'HT1', 'HT2'])
        self.add_events(job, 'cpu', keys=['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq'])
        self.add_events(job, 'llite', dev='/share', keys=['open', 'read_bytes', 'write_bytes'])
        self.add_events(job, 'llite', dev='/work', keys=['open', 'read_bytes', 'write_bytes'])
        self.add_events(job, 'llite', dev='/scratch', keys=['open', 'read_bytes', 'write_bytes'])
        self.add_events(job, 'lnet', keys=['rx_bytes', 'tx_bytes'])
        self.add_events(job, 'ib_sw', keys=['rx_bytes', 'tx_bytes'])
        self.add_events(job, 'net', keys=['rx_bytes', 'tx_bytes'])
        self.add_gauges(job, 'mem', keys=['MemTotal', 'MemUsed', 'FilePages', 'Mapped', 'AnonPages', 'Slab'])
        self.add_events(job, 'vm', keys=['pgactivate', 'pgdeactivate'])
    def add_info(self, col, val):
        self.cols.append(col)
        self.dict[col] = val
    def add_key_val(self, type_name, dev, key, val):
        if dev:
            col = type_name + ':' + dev + ':' + key
        else:
            col = type_name + ':' + key
        self.cols.append(col)
        self.dict[col] = val
    def add_events(self, job, type_name, dev=None, keys=None):
        schema = job.get_schema(type_name)
        if not schema:
            for key in keys:
                self.add_key_val(type_name, dev, key, '-')
            return
        vals = numpy.zeros(len(schema.entries), numpy.uint64)
        for host in job.hosts.itervalues():
            type_data = host.types[type_name]
            if dev:
                vals += type_data.stats[dev][-1]
            else:
                for stats in type_data.stats.itervalues():
                    vals += stats[-1]
        for key in keys:
            self.add_key_val(type_name, dev, key, vals[schema.keys[key].index])
    def add_gauges(self, job, type_name, dev=None, keys=None):
        schema = job.get_schema('mem')
        if not schema:
            for key in keys:
                self.add_key_val(type_name, dev, key, '-')
            return
        vals = numpy.zeros(len(schema.entries), numpy.uint64)
        for host in job.hosts.itervalues():
            type_data = host.types[type_name]
            if dev:
                nr_times = len(type_data.times[dev])
            else:
                nr_times = len(first_value(type_data.times))
            if nr_times == 0:
                continue
            if dev:
                stats = type_data.stats[dev]
            else:
                stats = sum(type_data.stats.itervalues()) # Sum over all devices.
            if nr_times == 1 or nr_times == 2:
                vals += stats[-1]
            else:
                vals += sum(stats[1:-1]) / (nr_times - 2) # Interior average.
        for key in keys:
            self.add_key_val(type_name, dev, key, vals[schema.keys[key].index])
    def print_header(self):
        print '\t'.join(self.cols)
    def print_values(self):
        print '\t'.join([str(self.dict[col]) for col in self.cols])
    def display(self):
        col_width = 32 # max(len(col) for col in self.cols) + 1
        val_width = 32 # max(len(str(val)) for val in self.dict.itervalues()) + 1
        for col in self.cols:
            print (col + ' ').ljust(col_width, '.') + (' ' + str(self.dict[col])).rjust(val_width, '.')


def display_job_report(info):
    try:
        id = info.get("id")
        if not id:
            job_stats.error("no id in job info\n")
            return
        job = job_stats.Job(id, info=info)
        if len(job.hosts) == 0:
            job_stats.error("job `%s' has no good hosts, skipping\n", job.id)
            return
        report = Report(job)
        report.display()
        print
    except:
        pass


if __name__ == '__main__':
    job_stats.verbose = False
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            job_info = job_stats.get_job_info(arg)
            if job_info:
                display_job_report(job_info)
    else:
        job_info = {}
        for line in sys.stdin:
            key, sep, val = line.strip().partition(" ")
            if key != "":
                job_info[key] = val
            elif len(job_info) != 0:
                display_job_report(job_info)
                job_info = {}
        if len(job_info) != 0:
            display_job_report(job_info)
