import numpy

def perf_event(event_select, unit_mask):
    return event_select | (unit_mask << 8) | (1L << 16) | (1L << 17) | (1L << 21) | (1L << 22)

#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x20)
#define SSE_DOUBLE_SCALAR_PACKED       PERF_EVENT(0x10, 0x90)
#define SIMD_FP_256_PACKED_DOUBLE      PERF_EVENT(0x11, 0x02)
#define L1D_REPLACEMENT                PERF_EVENT(0x51, 0x01) 
#define RESOURCE_STALLS_ANY            PERF_EVENT(0xA2, 0x01) 
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0xD0, 0x81) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_L1_HIT   PERF_EVENT(0xD1, 0x01) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_L2_HIT   PERF_EVENT(0xD1, 0x02) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_LLC_HIT  PERF_EVENT(0xD1, 0x04) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_LLC_MISS PERF_EVENT(0xD1, 0x20) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_HIT_LFB  PERF_EVENT(0xD1, 0x40) /* PMC0-3 only */


mem_uops_retired_all_loads    = perf_event(0xD0,0x81)
mem_load_uops_retired_L1_hit  = perf_event(0xD1,0x01)
mem_load_uops_retired_L2_hit  = perf_event(0xD1,0x02)
mem_load_uops_retired_LLC_hit = perf_event(0xD1,0x04)
sse_double_scalar_packed      = perf_event(0x10,0x90)
simd_fp_256_packed_double     = perf_event(0x11,0x02)
resource_stalls_any           = perf_event(0xA2,0x01)
L1d_replacement               = perf_event(0x51,0x01)

pmc_schema_desc = 'CTL0,C CTL1,C CTL2,C CTL3,C CTL4,C CTL5,C CTL6,C CTL7,C CTR0,E,W=48 CTR1,E,W=48 CTR2,E,W=48 CTR3,E,W=48 CTR4,E,W=48 CTR5,E,W=48 CTR6,E,W=48 CTR7,E,W=48 FIXED_CTR0,E,W=48 FIXED_CTR1,E,W=48 FIXED_CTR2,E,W=48\n'

core_schema_desc = 'OP_LOADS,E OP_LOADS_L1_HIT,E OP_LOADS_L2_HIT,E OP_LOADS_LLC_HIT,E SSE_DP,E 256_DP,E STALLS,E L1_REPLACEMENT,E INSTRUCTIONS_RETIRED,E CLOCKS_UNHALTED,E CLOCKS_UNHALTED_REF,E' # mult is handled below.

ctr_info = {
    #                                (is_prog, col, mult)
    mem_uops_retired_all_loads:      (True,      0,    1),
    mem_load_uops_retired_L1_hit:    (True,      1,    1),
    mem_load_uops_retired_L2_hit:    (True,      2,    1),
    mem_load_uops_retired_LLC_hit:   (True,      3,    1),
    sse_double_scalar_packed:        (True,      4,    1),
    simd_fp_256_packed_double:       (True,      5,    1),
    L1d_replacement:                 (True,      6,    1),
    resource_stalls_any:             (True,      7,    1),    
}

ctl_values = [mem_uops_retired_all_loads, mem_load_uops_retired_L1_hit, mem_load_uops_retired_L2_hit, mem_load_uops_retired_LLC_hit, sse_double_scalar_packed, simd_fp_256_packed_double, L1d_replacement, resource_stalls_any]

nr_core_ctrs = 11
nr_sock_ctrs = 0

nr_cores = 16
nr_socks = 2

def core_to_sock(c):
    return c / (nr_cores / nr_socks)

def process_host(host, times):
    pmc_stats = host.stats['intel_snb']
    core_stats = dict((str(i), numpy.zeros((len(times), nr_core_ctrs), numpy.uint64)) \
                      for i in range(0, nr_cores))

    for c_name, pmc_arr in pmc_stats.iteritems():
        if not c_name.isdigit():
            # XXX
            return
        c = int(c_name)
        if not (0 <= c and c < nr_cores):
            # XXX
            return
        if pmc_arr.shape != (len(times), 19):
            # XXX
            return
        core_arr = core_stats[c_name]

        for i, v in enumerate(pmc_arr):
            if not all(v[0:len(ctl_values)] == ctl_values):
                return
            for j in range(0, len(ctl_values)):

                is_prog, col, mult = ctr_info[v[j]]
                if is_prog:
                    core_arr[i, col] = mult * v[j + len(ctl_values)]

            core_arr[i, 8]  = v[len(ctl_values) + 8]
            core_arr[i, 9]  = v[len(ctl_values) + 9]
            core_arr[i, 10] = v[len(ctl_values) + 10]

    host.stats['snb_core'] = core_stats
    del host.stats['intel_snb']

def process_job(job):
    pmc_schema = job.schemas.get('intel_snb')
    if not pmc_schema:
        return
    if pmc_schema.desc != pmc_schema_desc:
        # XXX
        return
    core_schema = job.get_schema('snb_core', core_schema_desc)
    for host in job.hosts.itervalues():
        if 'intel_snb' not in host.stats: 
            del job.schemas['intel_snb']
            return

        process_host(host, job.times)
    del job.schemas['intel_snb']
