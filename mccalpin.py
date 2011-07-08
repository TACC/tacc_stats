#!/opt/apps/python/2.7.1/bin/python
import human, job_stats, numpy, os, signal, string, sys

sock_schema_desc = 'DRAM,E HT0,E HT1,E HT2,E'
sock_stats_cols = [(str(sock), key) for sock in range(0, 4) for key in ['DRAM', 'HT0', 'HT1', 'HT2']]
sock_stats_hdr = " ".join(sock + ":" + key for sock, key in sock_stats_cols)

core_schema_desc = 'USER,E DCSF,E SSE_FLOPS,E'
core_stats_cols = [(str(core), key) for core in range(0, 16) for key in ['USER', 'DCSF', 'SSE_FLOPS']]
core_stats_hdr = " ".join(core + ":" + key for core, key in core_stats_cols)

def mcc_sock_stats(job):
    sock_schema = job.get_schema('amd64_sock')
    if not sock_schema or sock_schema.desc != sock_schema_desc:
        job_stats.error("job `%s' has bad or missing amd64_sock data\n", job.id)
        return None
    for host, host_entry in job.hosts.iteritems():
        sock_data = host_entry.types['amd64_sock']
        # XXX times strictly increasing?
        times = sock_data.times['0']
        d_times = numpy.diff(times, axis=0)
        sock_stats = numpy.zeros((len(d_times), len(sock_stats_cols)), numpy.float64)
        for j0, col in enumerate(sock_stats_cols):
            sock = col[0]
            j1 = sock_schema.keys[col[1]].index
            sock_stats[:, j0] = numpy.diff(sock_data.stats[sock][:, j1], axis=0) / d_times
        print "TIME HOST " + sock_stats_hdr
        t0 = times[0]
        for i, t in enumerate(times[:-1]):
            print t - t0, host,
            for val in sock_stats[i, :]:
                print val,
            print

def print_mcc_stats(job):
    sock_schema = job.get_schema('amd64_sock')
    if not sock_schema or sock_schema.desc != sock_schema_desc:
        job_stats.error("job `%s' has bad or missing amd64_sock data\n", job.id)
        return
    core_schema = job.get_schema('amd64_core')
    if not core_schema or core_schema.desc != core_schema_desc:    
        job_stats.error("job `%s' has bad or missing amd64_core data\n", job.id)
        return
    print "TIME", "HOST", sock_stats_hdr, core_stats_hdr
    for host, host_entry in job.hosts.iteritems():
        sock_data = host_entry.types['amd64_sock']
        # XXX times strictly increasing?
        times = sock_data.times['0']
        d_times = numpy.diff(times, axis=0)
        sock_stats = numpy.zeros((len(d_times), len(sock_stats_cols)), numpy.float64)
        for j0, col in enumerate(sock_stats_cols):
            sock = col[0]
            j1 = sock_schema.keys[col[1]].index
            sock_stats[:, j0] = numpy.diff(sock_data.stats[sock][:, j1], axis=0) / d_times
        core_data = host_entry.types['amd64_core']
        core_stats = numpy.zeros((len(d_times), len(core_stats_cols)), numpy.float64)
        for j0, col in enumerate(core_stats_cols):
            core = col[0]
            j1 = core_schema.keys[col[1]].index
            core_stats[:, j0] = numpy.diff(core_data.stats[core][:, j1], axis=0) / d_times
        t0 = times[0]
        for i, t in enumerate(times[:-1]):
            print t - t0, host,
            for val in sock_stats[i, :]:
                print val,
            for val in core_stats[i, :]:
                print val,
            print

if __name__ == '__main__':
    job_stats.verbose = False
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: %s JOBID" % os.path.basename(sys.argv[0])
        sys.exit(1)
    id = sys.argv[1]
    info = job_stats.get_job_info(id)
    if not info:
        print >>sys.stderr, "%s: no info for job `%s'" % (os.path.basename(sys.argv[0]), id)
        sys.exit(1)
    job = job_stats.Job(id, info=info)
    if len(job.hosts) == 0:
        print >>sys.stderr, "%s: job `%s' has no good hosts" % (os.path.basename(sys.argv[0]), id)
        sys.exit(1)
    print_mcc_stats(job)
