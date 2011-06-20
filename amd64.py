import job_stats, numpy

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

def process_amd64(job):
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
