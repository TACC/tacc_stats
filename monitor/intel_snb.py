import numpy

def core_event(event_select, unit_mask):
    return event_select | (unit_mask << 8) | (1L << 16) | (1L << 17) | (1L << 21) | (1L << 22)
cpu_event_map = {
    core_event(0xD0,0x81) : 'LOAD_OPS_ALL',
    core_event(0xD1,0x01) : 'LOAD_OPS_L1_HIT', 
    core_event(0xD1,0x02) : 'LOAD_OPS_L2_HIT', 
    core_event(0xD1,0x04) : 'LOAD_OPS_LLC_HIT', 
    core_event(0x10,0x90) : 'SSE_D_ALL',
    core_event(0x11,0x02) : 'SIMD_D_256',
    core_event(0xA2,0x01) : 'STALLS',
    core_event(0x51,0x01) : 'LOAD_L1D_ALL',
    0                     : 'INSTRUCTIONS_RETIRED',
    1                     : 'CLOCKS_UNHALTED_CORE',
    2                     : 'CLOCKS_UNHALTED_REF'
}
intel_snb_schema_desc = 'CTL0,C CTL1,C CTL2,C CTL3,C CTL4,C CTL5,C CTL6,C CTL7,C CTR0,E,W=48 CTR1,E,W=48 CTR2,E,W=48 CTR3,E,W=48 CTR4,E,W=48 CTR5,E,W=48 CTR6,E,W=48 CTR7,E,W=48 FIXED_CTR0,E,W=48 FIXED_CTR1,E,W=48 FIXED_CTR2,E,W=48\n'


def CBOX_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 17) | (0L << 18) | (0L << 19) | (1L << 22) | (0L << 23) | (1L << 24)
cbo_event_map = {
    CBOX_PERF_EVENT(0x00, 0x00) : 'CLOCK_TICKS',
    CBOX_PERF_EVENT(0x11, 0x01) : 'RxR_OCCUPANCY',
    CBOX_PERF_EVENT(0x1F, 0x00) : 'COUNTER0_OCCUPANCY',
    CBOX_PERF_EVENT(0x34, 0x03) : 'LLC_LOOKUP'
    }
intel_cbo_schema_desc = 'CTL0,C CTL1,C CTL2,C CTL3,C CTR0,E,W=44 CTR1,E,W=44 CTR2,E,W=44 CTR3,E,W=44\n'

# CTL registers must be first, followed py programmable registers, 
# followed by fixed registers
def register(job, host, name, event_map):
    schema_desc = job.schemas.get(name).desc
    
    stats = host.stats[name]
    registers = schema_desc.split()

    ctl_registers =[]
    ctr_registers =[]

    for reg in registers:    
        if reg.split(',')[1] != 'C': ctr_registers.append(registers.index(reg))
        else: ctl_registers.append(registers.index(reg))

    # Build Schema from ctl registers and event maps
    dev_schema = []
    for dev, array in stats.iteritems():
        for j in ctl_registers:
            dev_schema.append(event_map[array[0,j]])
        break

    # Schema appended for fixed ctrs 
    nr_fixed = len(ctr_registers) - len(ctl_registers)
    for i in range(0,nr_fixed):
        dev_schema.append(event_map[i])

    dev_schema_desc = ' '.join(dev_schema) + '\n'

    # Build stats without ctl registers
    dev_stats = dict((str(i), numpy.zeros((len(job.times),len(ctr_registers)),numpy.uint64)) for i in stats.keys())

    for dev, array in stats.iteritems():
        data = dev_stats[dev]
        for j in ctr_registers:                
            data[:,j - len(ctl_registers)] = numpy.array(array[:,j], numpy.uint64)

    del job.schemas[name], host.stats[name]

    job.get_schema(name, dev_schema_desc)
    host.stats[name] = dev_stats


def process_job(job):

    for host in job.hosts.itervalues():
        if 'intel_snb' in job.schemas:
            register(job, host,'intel_snb',cpu_event_map)
        if 'intel_snb_cbo' in job.schemas:
            register(job, host, 'intel_snb_cbo',cbo_event_map)

        print job.schemas.get('intel_snb').desc
        print host.stats['intel_snb']

        print job.schemas.get('intel_snb_cbo').desc
        print host.stats['intel_snb_cbo']
