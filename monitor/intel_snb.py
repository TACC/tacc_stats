import numpy

# Post-processing for core and uncore SNB events are performed in this file
# for the pickler. 

# The registers must be reported in the following order in the stats file:
# 1) CTL registers
# 2) Programmable CTR registers
# 3) Fixed CTR registers

# Core events
def CORE_PERF_EVENT(event_select, unit_mask):
    return event_select | (unit_mask << 8) | (1L << 16) | (1L << 17) | (1L << 21) | (1L << 22)
cpu_event_map = {
    CORE_PERF_EVENT(0xD0,0x81) : 'LOAD_OPS_ALL,E',
    CORE_PERF_EVENT(0xD1,0x01) : 'LOAD_OPS_L1_HIT,E', 
    CORE_PERF_EVENT(0xD1,0x02) : 'LOAD_OPS_L2_HIT,E', 
    CORE_PERF_EVENT(0xD1,0x04) : 'LOAD_OPS_LLC_HIT,E', 
    CORE_PERF_EVENT(0x10,0x90) : 'SSE_D_ALL,E',
    CORE_PERF_EVENT(0x11,0x02) : 'SIMD_D_256,E',
    CORE_PERF_EVENT(0xA2,0x01) : 'STALLS,E',
    CORE_PERF_EVENT(0x51,0x01) : 'LOAD_L1D_ALL,E',
    'FIXED0'                   : 'INSTRUCTIONS_RETIRED,E',
    'FIXED1'                   : 'CLOCKS_UNHALTED_CORE,E',
    'FIXED2'                   : 'CLOCKS_UNHALTED_REF,E'
}
# CBo events
def CBOX_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 17) | (0L << 18) | (0L << 19) | (1L << 22) | (0L << 23) | (1L << 24)
cbo_event_map = {
    CBOX_PERF_EVENT(0x00, 0x00) : 'CLOCK_TICKS,E',
    CBOX_PERF_EVENT(0x11, 0x01) : 'RxR_OCCUPANCY,E',
    CBOX_PERF_EVENT(0x1F, 0x00) : 'COUNTER0_OCCUPANCY,E',
    CBOX_PERF_EVENT(0x34, 0x03) : 'LLC_LOOKUP,E'
    }
# Home Agent Unit events
def HAU_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L << 23) | (1L << 24)
hau_event_map = {
    HAU_PERF_EVENT(0x01, 0x03) : 'READ_REQUESTS,E',
    HAU_PERF_EVENT(0x01, 0x0C) : 'WRITE_REQUESTS,E',
    HAU_PERF_EVENT(0x00, 0x00) : 'CLOCKTICKS,E',
    HAU_PERF_EVENT(0x1A, 0x0F) : 'IMC_WRITES,E'
    }
#iMC events
def IMC_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24)
imc_event_map = {
    IMC_PERF_EVENT(0x04, 0x03) : 'CAS_READS,E',
    IMC_PERF_EVENT(0x04, 0x0C) : 'CAS_WRITES,E',
    IMC_PERF_EVENT(0x01, 0x00) : 'ACT_COUNT,E',
    IMC_PERF_EVENT(0x02, 0x03) : 'PRE_COUNT_ALL,E',              
    'FIXED0'                   : 'CYCLES,E'
    }
#Power Control Unit events
def PCU_PERF_EVENT(event):
    return (event) | (0L << 14) | (0L << 17) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24) | (0L << 31)
pcu_event_map = {
    PCU_PERF_EVENT(0x06) : 'MAX_OS_CYCLES,E',
    PCU_PERF_EVENT(0x07) : 'MAX_CURRENT_CYCLES,E',
    PCU_PERF_EVENT(0x04) : 'MAX_TEMP_CYCLES,E',
    PCU_PERF_EVENT(0x05) : 'MAX_POWER_CYCLES,E',              
    PCU_PERF_EVENT(0x81) : 'MIN_IO_CYCLES,E',              
    PCU_PERF_EVENT(0x82) : 'MIN_SNOOP_CYCLES,E',              
    'FIXED0'             : 'C3_CYCLES,E',
    'FIXED1'             : 'C6_CYCLES,E'
    }
#QPI Unit events
def QPI_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24)
qpi_event_map = {
    QPI_PERF_EVENT(0x00, 0x01) : 'G0_IDLE,E',
    QPI_PERF_EVENT(0x00, 0x04) : 'G0_NON_DATA,E',
    QPI_PERF_EVENT(0x02, 0x08) : 'G1_DRS_DATA,E',
    QPI_PERF_EVENT(0x03, 0x04) : 'G2_NCB_DATA,E',              
    }
#R2PCI Unit events
def R2PCI_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24)
r2pci_event_map = {
    R2PCI_PERF_EVENT(0x24, 0x04) : 'TRANSMITS,E',
    R2PCI_PERF_EVENT(0x01, 0x00) : 'CLOCKTICKS,E',
    R2PCI_PERF_EVENT(0x07, 0x0F) : 'ADDRESS_USED,E',
    R2PCI_PERF_EVENT(0x08, 0x0F) : 'ACKNOWLEDGED_USED,E',              
    R2PCI_PERF_EVENT(0x09, 0x0F) : 'DATA_USED,E',              
    }

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
        dev_schema.append(event_map['FIXED'+str(i)])

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
        if 'intel_snb_hau' in job.schemas:
            register(job, host, 'intel_snb_hau',hau_event_map)
        if 'intel_snb_imc' in job.schemas:
            register(job, host, 'intel_snb_imc',imc_event_map)
        if 'intel_snb_pcu' in job.schemas:
            register(job, host, 'intel_snb_pcu',pcu_event_map)
        #if 'intel_snb_qpi' in job.schemas:
        #    register(job, host, 'intel_snb_qpi',qpi_event_map)
        if 'intel_snb_r2pci' in job.schemas:
            register(job, host, 'intel_snb_r2pci',r2pci_event_map)

        #for dev, data in hosts.stats['intel_snb_r2pci']:
        #    print dev
