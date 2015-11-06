## @file intel_process.py
# Post-processing for core and uncore NHM/WTM/SNB events 
# are performed in this file for the pickler. 
#
# The registers must be reported in the following order in the stats file:
# -# CTL registers
# -# Programmable CTR registers
# -# Fixed CTR registers
# -# If CTL register programming failed it (QPI) it seems to be 0, so this is added to event maps
# ---->>>> Programmable CTL registers must be in same order as CTR 
import numpy

## Processor events
def CORE_PERF_EVENT(event_select, unit_mask):
    return event_select | (unit_mask << 8) | (1L << 16) | (1L << 17) | (0L << 21) | (1L << 22)
def CORE_PERF_EVENT1(event_select, unit_mask):
    return event_select | (unit_mask << 8) | (1L << 16) | (1L << 17) | (1L << 21) | (1L << 22)
## Processor event map
cpu_event_map = {
    CORE_PERF_EVENT(0xD0,0x81) : 'LOAD_OPS_ALL,E',
    CORE_PERF_EVENT(0xD1,0x01) : 'LOAD_OPS_L1_HIT,E', 
    CORE_PERF_EVENT(0xD1,0x02) : 'LOAD_OPS_L2_HIT,E', 
    CORE_PERF_EVENT(0xD1,0x04) : 'LOAD_OPS_LLC_HIT,E', 
    CORE_PERF_EVENT(0xD1,0x20) : 'MEM_LOAD_UOPS_RETIRED_LLC_MISS,E',
    CORE_PERF_EVENT(0xD1,0x40) : 'MEM_LOAD_UOPS_RETIRED_HIT_LFB,E',
    CORE_PERF_EVENT(0xD1,0x08) : 'MEM_LOAD_UOPS_RETIRED_L1_MISS,E',
    CORE_PERF_EVENT(0xD1,0x10) : 'MEM_LOAD_UOPS_RETIRED_L2_MISS,E',
    CORE_PERF_EVENT(0xD1,0x20) : 'MEM_LOAD_UOPS_RETIRED_L3_MISS,E',
    CORE_PERF_EVENT(0x10,0x90) : 'SSE_DOUBLE_ALL,E',
    CORE_PERF_EVENT(0x11,0x02) : 'SIMD_DOUBLE_256,E',
    CORE_PERF_EVENT(0xA2,0x01) : 'STALLS,E',
    CORE_PERF_EVENT(0x51,0x01) : 'LOAD_L1D_ALL,E',
    CORE_PERF_EVENT(0x10,0x80) : 'SSE_DOUBLE_SCALAR,E',
    CORE_PERF_EVENT(0x10,0x10) : 'SSE_DOUBLE_PACKED,E',
    CORE_PERF_EVENT(0xF1,0x07) : 'L2_LINES_IN_ALL,E',
    CORE_PERF_EVENT1(0xD0,0x81) : 'LOAD_OPS_ALL,E',
    CORE_PERF_EVENT1(0xD1,0x01) : 'LOAD_OPS_L1_HIT,E', 
    CORE_PERF_EVENT1(0xD1,0x02) : 'LOAD_OPS_L2_HIT,E', 
    CORE_PERF_EVENT1(0xD1,0x04) : 'LOAD_OPS_LLC_HIT,E', 
    CORE_PERF_EVENT1(0xD1,0x20) : 'MEM_LOAD_UOPS_RETIRED_LLC_MISS,E',
    CORE_PERF_EVENT1(0xD1,0x40) : 'MEM_LOAD_UOPS_RETIRED_HIT_LFB,E',
    CORE_PERF_EVENT1(0xD1,0x08) : 'MEM_LOAD_UOPS_RETIRED_L1_MISS,E',
    CORE_PERF_EVENT1(0xD1,0x10) : 'MEM_LOAD_UOPS_RETIRED_L2_MISS,E',
    CORE_PERF_EVENT1(0xD1,0x20) : 'MEM_LOAD_UOPS_RETIRED_L3_MISS,E',
    CORE_PERF_EVENT1(0x10,0x90) : 'SSE_DOUBLE_ALL,E',
    CORE_PERF_EVENT1(0x11,0x02) : 'SIMD_DOUBLE_256,E',
    CORE_PERF_EVENT1(0xA2,0x01) : 'STALLS,E',
    CORE_PERF_EVENT1(0x51,0x01) : 'LOAD_L1D_ALL,E',
    CORE_PERF_EVENT1(0x10,0x80) : 'SSE_DOUBLE_SCALAR,E',
    CORE_PERF_EVENT1(0x10,0x10) : 'SSE_DOUBLE_PACKED,E',
    CORE_PERF_EVENT1(0xF1,0x07) : 'L2_LINES_IN_ALL,E',
    'FIXED0'                   : 'INSTRUCTIONS_RETIRED,E',
    'FIXED1'                   : 'CLOCKS_UNHALTED_CORE,E',
    'FIXED2'                   : 'CLOCKS_UNHALTED_REF,E',
}

## CBo events
def CBOX_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 17) | (0L << 18) | (0L << 19) | (1L << 22) | (0L << 23) | (1L << 24)
## CBo event map
cbo_event_map = {
    CBOX_PERF_EVENT(0x00, 0x00) : 'CLOCK_TICKS,E',
    CBOX_PERF_EVENT(0x11, 0x01) : 'RxR_OCCUPANCY,E',
    CBOX_PERF_EVENT(0x1F, 0x00) : 'COUNTER0_OCCUPANCY,E',
    CBOX_PERF_EVENT(0x34, 0x03) : 'LLC_LOOKUP_DATA_READ,E',
    CBOX_PERF_EVENT(0x34, 0x11) : 'LLC_LOOKUP_ANY,E',
    CBOX_PERF_EVENT(0x34, 0x05) : 'LLC_LOOKUP_WRITE,E',
    CBOX_PERF_EVENT(0x1E, 0x0F) : 'RING_IV_USED,E'
    }

## Home Agent Unit events
def HAU_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L << 23) | (1L << 24)
## Home Agent map
hau_event_map = {
    HAU_PERF_EVENT(0x01, 0x03) : 'READ_REQUESTS,E',
    HAU_PERF_EVENT(0x01, 0x0C) : 'WRITE_REQUESTS,E',
    HAU_PERF_EVENT(0x00, 0x00) : 'CLOCKTICKS,E',
    HAU_PERF_EVENT(0x1A, 0x0F) : 'IMC_WRITES,E',
    }

## Integrated Memory events
def IMC_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24)
## Integrated Memory Controller map
imc_event_map = {
    IMC_PERF_EVENT(0x04, 0x03) : 'CAS_READS,E',
    IMC_PERF_EVENT(0x04, 0x0C) : 'CAS_WRITES,E',
    IMC_PERF_EVENT(0x01, 0x00) : 'ACT_COUNT,E',
    IMC_PERF_EVENT(0x02, 0x03) : 'PRE_COUNT_ALL,E',              
    IMC_PERF_EVENT(0x02, 0x01) : 'PRE_COUNT_MISS,E',              
    'FIXED0'                   : 'CYCLES,E',
    }

## Power Control Unit events
def PCU_PERF_EVENT(event):
    return (event) | (0L << 14) | (0L << 17) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24) | (0L << 31)
## Power Control map
pcu_event_map = {
    PCU_PERF_EVENT(0x06) : 'MAX_OS_CYCLES,E',
    PCU_PERF_EVENT(0x07) : 'MAX_CURRENT_CYCLES,E',
    PCU_PERF_EVENT(0x04) : 'MAX_TEMP_CYCLES,E',
    PCU_PERF_EVENT(0x05) : 'MAX_POWER_CYCLES,E',              
    PCU_PERF_EVENT(0x81) : 'MIN_IO_CYCLES,E',              
    PCU_PERF_EVENT(0x82) : 'MIN_SNOOP_CYCLES,E',              
    'FIXED0'             : 'C3_CYCLES,E',
    'FIXED1'             : 'C6_CYCLES,E',
    }

## QPI Unit events
def QPI_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 21) | (1L << 22) | (0L <<23)
## QPI map
qpi_event_map = {
    QPI_PERF_EVENT(0x00, 0x01) : 'TxL_FLITS_G1_SNP,E',
    QPI_PERF_EVENT(0x00, 0x04) : 'TxL_FLITS_G1_HOM,E',
    QPI_PERF_EVENT(0x02, 0x08) : 'G1_DRS_DATA,E',
    QPI_PERF_EVENT(0x03, 0x04) : 'G2_NCB_DATA,E',              
    }

## R2PCI Unit events
def R2PCI_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (0L << 18) | (1L << 22) | (0L <<23) | (1L << 24)
## R2PCI map
r2pci_event_map = {
    R2PCI_PERF_EVENT(0x24, 0x04) : 'TRANSMITS,E',
    R2PCI_PERF_EVENT(0x01, 0x00) : 'CLOCKTICKS,E',
    R2PCI_PERF_EVENT(0x07, 0x0F) : 'ADDRESS_USED,E',
    R2PCI_PERF_EVENT(0x08, 0x0F) : 'ACKNOWLEDGED_USED,E',              
    R2PCI_PERF_EVENT(0x09, 0x0F) : 'DATA_USED,E',              
    }

## WESTMERE events
def WTM_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (1L << 16) | (1L << 17) | (1L <<21) | (1L << 22)
## WTM map
wtm_event_map = {
    WTM_PERF_EVENT(0x0F, 0x10) : 'MEM_UNCORE_RETIRED_REMOTE_DRAM,E',
    WTM_PERF_EVENT(0x0F, 0x20) : 'MEM_UNCORE_RETIRED_LOCAL_DRAM,E',
    WTM_PERF_EVENT(0x10, 0x01) : 'FP_COMP_OPS_EXE_X87,E',
    WTM_PERF_EVENT(0x10, 0x10) : 'FP_COMP_OPS_EXE_SSE_PACKED,E',
    WTM_PERF_EVENT(0x10, 0x20) : 'FP_COMP_OPS_EXE_SSE_SCALAR,E',
    WTM_PERF_EVENT(0xCB, 0x01) : 'MEM_LOAD_RETIRED_L1D_HIT,E',              
    'FIXED0'                   : 'INSTRUCTIONS_RETIRED,E',
    'FIXED1'                   : 'CLOCKS_UNHALTED_CORE,E',
    'FIXED2'                   : 'CLOCKS_UNHALTED_REF,E',
    }
## WESTMERE UNCORE events
def WTMUNC_PERF_EVENT(event, umask):
    return (event) | (umask << 8) | (1L << 22)
## WTM map
wtmunc_event_map = {
    WTMUNC_PERF_EVENT(0x08, 0x01) : 'L3_HITS_READ,E',
    WTMUNC_PERF_EVENT(0x08, 0x02) : 'L3_HITS_WRITE,E',
    WTMUNC_PERF_EVENT(0x08, 0x04) : 'L3_HITS_PROBE,E',
    WTMUNC_PERF_EVENT(0x09, 0x01) : 'L3_MISS_READ,E',
    WTMUNC_PERF_EVENT(0x09, 0x02) : 'L3_MISS_WRITE,E',
    WTMUNC_PERF_EVENT(0x09, 0x04) : 'L3_MISS_PROBE,E',
    WTMUNC_PERF_EVENT(0x0A, 0x0F) : 'L3_LINES_IN_ANY,E',
    WTMUNC_PERF_EVENT(0x0B, 0x1F) : 'L3_LINES_OUT_ANY,E',              
    'FIXED0'                      : 'CLOCKS_UNCORE,E',
    }

## Reformats the counter arrays with configurable events
class reformat_counters:

    ## Constructor
    def __init__(self, job, name, event_map):
        ## Job Object
        self.job = job
        ## Name of device
        self.name = name
        ## List of CTL registers
        self.ctl_registers = []
        ## List of CTR registers
        self.ctr_registers = []
        ## List of Fixed registers
        self.fix_registers = []

        # Just need the first hosts schema
        stats = None
        for host in job.hosts.itervalues():
            if name not in host.stats: return
            stats = host.stats[name]
            break
        
        if stats == None:
            return

        schema_desc = job.schemas.get(self.name).desc
        registers = schema_desc.split()

        for reg in registers:    
            if reg.split(',')[1] != 'C':
                if reg.find('FIXED') == -1:
                    self.ctr_registers.append(registers.index(reg))
                else:
                    self.fix_registers.append(registers.index(reg))
            else:
                if reg.find('GLOBAL') == -1 and reg.find('FIXED') == -1 and reg.find('OPCODE_MATCH') == -1:
                    self.ctl_registers.append(registers.index(reg))

        # Build Schema from ctl registers and event maps
        dev_schema = []
        for dev, array in stats.iteritems():
            for j in self.ctl_registers:
                dev_schema.append(event_map.get(array[0,j],str(array[0,j])))
            break


        # Now check for all hosts:
        # all devices have the same control settings
        # all devices control setting remain the same during the job
        for host in job.hosts.itervalues():
            if name in host.stats:
                for dev, array in host.stats[name].iteritems():
                    devidx = 0
                    for j in self.ctl_registers:
                        settings = array[:,j]
                        if event_map.get(settings[0],str(settings[0])) != dev_schema[devidx] or settings.min() != settings.max():
                            #if name in 'intel_snb': print host.name,dev,settings
                            #print '>>>>>>>>>>>>>>>>>>>>>error'
                            # The control settings for this device changed during the run
                            # mark as the error metric
                            dev_schema[devidx] = "ERROR,E"
                        devidx += 1

        # Schema appended for fixed ctrs 
        nr_fixed = len(self.fix_registers)
        for i in range(0,nr_fixed):
            dev_schema.append(event_map['FIXED'+str(i)])

        dev_schema_desc = ' '.join(dev_schema) + '\n'

        del self.job.schemas[self.name]
        self.job.get_schema(self.name, dev_schema_desc)

    ## Remap data to human readable schema
    def register(self,host):
        # Build stats without ctl registers
        if self.name not in host.stats: return
        stats = host.stats[self.name]
        dev_stats = dict((str(i), numpy.zeros((len(self.job.times),len(self.ctr_registers)+len(self.fix_registers)),numpy.uint64)) for i in stats.keys())

        for dev, array in stats.iteritems():
            data = dev_stats[dev]
            idx = 0
            for j in self.ctr_registers:                
                data[:,idx] = numpy.array(array[:,j], numpy.uint64)
                idx += 1
            for j in self.fix_registers:                
                data[:,idx] = numpy.array(array[:,j], numpy.uint64)
                idx += 1
                
        host.stats[self.name] = dev_stats

intel_xeon = {'intel_snb' : cpu_event_map, 'intel_snb_cbo' : cbo_event_map, 'intel_snb_hau' : hau_event_map, 
              'intel_snb_imc' : imc_event_map,  'intel_snb_qpi' : qpi_event_map, 'intel_snb_pcu' : pcu_event_map, 'intel_snb_r2pci' : r2pci_event_map,
              'intel_ivb' : cpu_event_map, 'intel_ivb_cbo' : cbo_event_map, 'intel_ivb_hau' : hau_event_map, 
              'intel_ivb_imc' : imc_event_map,  'intel_ivb_qpi' : qpi_event_map, 'intel_ivb_pcu' : pcu_event_map, 'intel_ivb_r2pci' : r2pci_event_map,
              'intel_hsw' : cpu_event_map, 'intel_hsw_cbo' : cbo_event_map, 'intel_hsw_hau' : hau_event_map, 
              'intel_hsw_imc' : imc_event_map,  'intel_hsw_qpi' : qpi_event_map, 'intel_hsw_pcu' : pcu_event_map, 'intel_hsw_r2pci' : r2pci_event_map,
              'intel_hsw_ht' : cpu_event_map, 'intel_hsw_cbo_ht' : cbo_event_map,
}


def process_job(job):
    print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>',cpu_event_map
    # These events work for SNB,IVB,HSW at this time 2015/05/27
    for device, mapping in intel_xeon.iteritems():
        if device in job.schemas:
            d = reformat_counters(job, device, mapping)
            for host in job.hosts.itervalues():
                d.register(host)

    # Backwards compatibility
    if 'intel_pmc3' in job.schemas:
        wtm = reformat_counters(job, 'intel_pmc3',wtm_event_map)
        for host in job.hosts.itervalues():
            wtm.register(host)

    if 'intel_wtm' in job.schemas:
        wtm = reformat_counters(job, 'intel_wtm',wtm_event_map)
        for host in job.hosts.itervalues():
            wtm.register(host)

    if 'intel_uncore' in job.schemas:
        wtmunc = reformat_counters(job, 'intel_uncore',wtmunc_event_map)
        for host in job.hosts.itervalues():
            wtmunc.register(host)

    # NHM has the same events as WTM (for our purposes)
    if 'intel_nhm' in job.schemas:
        nhm = reformat_counters(job, 'intel_nhm',wtm_event_map)
        for host in job.hosts.itervalues():
            nhm.register(host)
