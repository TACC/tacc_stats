import job, numpy

amd64_core_ctls = {
    user_cycles: 0,
    dcache_sys_fills: 1,
    sse_flops: 2,
    }

amd64_sock_ctls = {
    dram_accesses: 0,
    ht_link_0_use: 1,
    ht_link_1_use: 2,
    ht_link_2_use: 3,
    }

for host_entry in job.hosts.itervalues():
    orig_data = host_entry.types['amd64_pmc']
    core_data = host_entry.add_type('amd64_core', 'USER,E DCSF,E SSE_FLOPS,E')
    sock_data = host_entry.add_type('amd64_sock', 'DRAM,E HT0,E HT1,E HT2,E')
    # Assume no stray times.
    times = orig_data.times['0']
    nr_rows = len(times)
    for sock_nr in range(0, 4):
        sock_dev = str(sock_nr)
        sock_data.times[sock_dev] = numpy.array(times, numpy.uint64)
        sock_stats = sock_data.stats[sock_dev] = numpy.zeros((nr_rows, 4), numpy.uint64)
        for core_nr in range(4 * sock_nr, 4 * (sock_nr + 1)):
            core_dev = str(core_nr)
            orig_stats = orig_data.stats[core_dev]
            core_data.times[core_dev] = numpy.array(times, numpy.uint64)
            core_stats = core_data.stats[core_dev] = numpy.zeros((nr_rows, 3), numpy.uint64)
            # Assume schema is still CTL{0..3} CTR{0..3}.
            for row in range(0, nr_rows):
                for ctl_nr in range(0, 4):
                    ctl = orig_stats[row][ctl_nr]
                    val = orig_stats[row][ctl_nr + 4]
                    if ctl in amd64_sock_ctls:
                        sock_stats[row][amd64_sock_ctls[ctl]] += val
                    elif ctl in amd64_core_ctls:
                        core_stats[row][amd64_core_ctls[ctl]] += val
                    else:
                        error("unknown PMC control value %d\n", ctl)

job.types['amd64_core'].devs = set(map(str, range(0, 16)))
job.types['amd64_sock'].devs = set(map(str, range(0, 4)))
