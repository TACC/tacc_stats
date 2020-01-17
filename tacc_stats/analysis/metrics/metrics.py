import sys
import operator, traceback
import pickle as p
import multiprocessing
from tacc_stats.analysis.gen import utils
from numpy import diff, amax, zeros, maximum, mean, isnan, trapz

def _unwrap(args):
  try:
    return args[0].compute_metrics(args[1])
  except Exception as e:
    print(traceback.format_exc())    
    return

class Metrics():

  def __init__(self, metric_list, processes = 1):
    self.processes = processes
    self.metric_list = metric_list
    
  # Compute metrics in parallel (Shared memory only)
  def run(self, filelist):
    if not filelist: 
      print("Please specify a job file list.")
      sys.exit()
    pool = multiprocessing.Pool(processes = self.processes) 

    metrics = pool.map(_unwrap, zip([self]*len(filelist), filelist))
    #metrics = map(_unwrap, zip([self]*len(filelist), filelist))
    return metrics

  # Compute metric
  def compute_metrics(self, jobpath):
    try:
      with open(jobpath, 'rb') as fd: 
        try: job = p.load(fd)
        except UnicodeDecodeError as e: 
          try: 
            job = p.load(fd, encoding = "latin1") # Python2 Compatibility
          except: return jobpath, None
    except MemoryError as e:
      print('File ' + jobpath + ' to large to load')
      return jobpath, None
    except IOError as e:
      print('File ' + jobpath + ' not found')
      return jobpath, None
    except EOFError as e:
      print('End of file error for: ' + jobpath)
      return jobpath, None
    except:
      return jobpath, None
    u = utils.utils(job)
    _metrics = {}
    for name in self.metric_list:
      try:
        _metrics[name] = getattr(sys.modules[__name__], name)().compute_metric(u)
      except: 
        print(name + " failed for job " + job.id)
    return job.id, _metrics

###########
# Metrics #
###########

class avg_blockbw():
    def compute_metric(self, u):
      schema, _stats = u.get_type("block")
      blockbw = 0
      for hostname, stats in _stats.items():
        blockbw += stats[-1, schema["rd_sectors"].index] - stats[0, schema["rd_sectors"].index] + \
                   stats[-1, schema["wr_sectors"].index] - stats[0, schema["wr_sectors"].index]
      return blockbw/(u.dt*u.nhosts*1024*1024)

class avg_cpi():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    cycles = 0
    instrs = 0
    for hostname, stats in _stats.items():
      cycles += stats[-1, schema["CLOCKS_UNHALTED_CORE"].index] - \
                stats[0, schema["CLOCKS_UNHALTED_CORE"].index]
      instrs += stats[-1, schema["INSTRUCTIONS_RETIRED"].index] - \
                stats[0, schema["INSTRUCTIONS_RETIRED"].index] 
    return cycles/instrs

class avg_freq():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    cycles = 0
    cycles_ref = 0
    for hostname, stats in _stats.items():
      cycles += stats[-1, schema["CLOCKS_UNHALTED_CORE"].index] - \
                stats[0, schema["CLOCKS_UNHALTED_CORE"].index]
      cycles_ref += stats[-1, schema["CLOCKS_UNHALTED_REF"].index] - \
                    stats[0, schema["CLOCKS_UNHALTED_REF"].index] 
    return u.freq*cycles/cycles_ref

class avg_cpuusage():
  def compute_metric(self, u):
    schema, _stats = u.get_type("cpu")    
    cpu = 0
    for hostname, stats in _stats.items():
      cpu += stats[-1, schema["user"].index] - stats[0, schema["user"].index]
    return cpu/(u.dt*u.nhosts*100)

class avg_ethbw():
    def compute_metric(self, u):
        schema, _stats = u.get_type("net")
        bw = 0
        for hostname, stats in _stats.items():
            bw += stats[-1, schema["rx_bytes"].index] - stats[0, schema["rx_bytes"].index] + \
                  stats[-1, schema["tx_bytes"].index] - stats[0, schema["tx_bytes"].index]
        return bw/(u.dt*u.nhosts*1024*1024)

class avg_fabricbw():
    def compute_metric(self, u):
        avg = 0
        try:
            schema, _stats = u.get_type("ib_ext")              
            tb, rb = schema["port_xmit_data"].index, schema["port_rcv_data"].index
            conv2mb = 1024*1024
        except:
            schema, _stats = u.get_type("opa")  
            tb, rb = schema["PortXmitData"].index, schema["PortRcvData"].index
            conv2mb = 125000
        for hostname, stats in _stats.items():
            avg += stats[-1, tb] + stats[-1, rb] - \
                   stats[0, tb] - stats[0, rb]
        return avg/(u.dt*u.nhosts*conv2mb)

class avg_flops_64b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"SSE_D_ALL" : 1, "SIMD_D_256" : 2, 
                    "FP_ARITH_INST_RETIRED_SCALAR_DOUBLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE" : 2, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE" : 4, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE" : 8, 
                     "SSE_DOUBLE_SCALAR" : 1, 
                     "SSE_DOUBLE_PACKED" : 2, 
                     "SIMD_DOUBLE_256" : 4}
    flops = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths:
          index = schema[eventname].index
          flops += (stats[-1, index] - stats[0, index])*vector_widths[eventname]
    return flops/(u.dt*u.nhosts*1e9)

class avg_flops_32b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"FP_ARITH_INST_RETIRED_SCALAR_SINGLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_SINGLE" : 4, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_SINGLE" : 8, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_SINGLE" : 16}
    flops = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths:
          index = schema[eventname].index
          flops += (stats[-1, index] - stats[0, index])*vector_widths[eventname]
    return flops/(u.dt*u.nhosts*1e9)


class avg_l1loadhits():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    load_names = ['LOAD_OPS_L1_HIT', 'MEM_UOPS_RETIRED_L1_HIT_LOADS']
    loads = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in load_names:
          index = schema[eventname].index
          loads += stats[-1, index] - stats[0, index]
    return loads/(u.dt*u.nhosts)

class avg_l2loadhits():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    load_names = ['LOAD_OPS_L2_HIT', 'MEM_UOPS_RETIRED_L2_HIT_LOADS']
    loads = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in load_names:
          index = schema[eventname].index
          loads += stats[-1, index] - stats[0, index]
    return loads/(u.dt*u.nhosts)

class avg_llcloadhits():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    load_names = ['LOAD_OPS_LLC_HIT', 'MEM_UOPS_RETIRED_LLC_HIT_LOADS']
    loads = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in load_names:
          index = schema[eventname].index
          loads += stats[-1, index] - stats[0, index]
    return loads/(u.dt*u.nhosts)

class avg_lnetbw():
    def compute_metric(self, u):
        schema, _stats = u.get_type("lnet")
        bw = 0
        for hostname, stats in _stats.items():
            bw += stats[-1, schema["rx_bytes"].index] + stats[-1, schema["tx_bytes"].index] \
                  - stats[0, schema["rx_bytes"].index] - stats[0, schema["tx_bytes"].index]
        return bw/(1024*1024*u.dt*u.nhosts)

class avg_lnetmsgs():
    def compute_metric(self, u):
        avg = 0
        schema, _stats = u.get_type("lnet")                  
        tx, rx = schema["tx_msgs"].index, schema["rx_msgs"].index

        for hostname, stats in _stats.items():
            avg += stats[-1, tx] + stats[-1, rx] - \
                   stats[0, tx] - stats[0, rx]
        return avg/(u.dt*u.nhosts)

class avg_loads():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    load_names = ['LOAD_OPS_ALL','MEM_UOPS_RETIRED_ALL_LOADS']
    loads = 0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in load_names:
          index = schema[eventname].index
          loads += stats[-1, index] - stats[0, index]
    return loads/(u.dt*u.nhosts)

class avg_mbw():
  def compute_metric(self, u):
    schema, _stats = u.get_type("imc")
    avg = 0
    for hostname, stats in _stats.items():
      avg += stats[-1, schema["CAS_READS"].index] + stats[-1, schema["CAS_WRITES"].index] \
             - stats[0, schema["CAS_READS"].index] - stats[0, schema["CAS_WRITES"].index]
    return 64.0*avg/(1024*1024*1024*u.dt*u.nhosts)

class avg_mcdrambw():
  def compute_metric(self, u):      
    avg = 0
    schema, _stats = u.get_type("intel_knl_edc_eclk")
    for hostname, stats in _stats.items():
      avg += stats[-1, schema["RPQ_INSERTS"].index] + stats[-1, schema["WPQ_INSERTS"].index] \
             - stats[0, schema["RPQ_INSERTS"].index] - stats[0, schema["WPQ_INSERTS"].index]

    if not "flat" in u.job.acct["queue"].lower():
      schema, _stats = u.get_type("intel_knl_edc_uclk")
      for hostname, stats in _stats.items():
        avg -= stats[-1, schema["EDC_MISS_CLEAN"].index] - stats[0, schema["EDC_MISS_CLEAN"].index] + \
               stats[-1, schema["EDC_MISS_DIRTY"].index] - stats[0, schema["EDC_MISS_DIRTY"].index]

      schema, _stats = u.get_type("intel_knl_mc_dclk")
      for hostname, stats in _stats.items():
        avg -= stats[-1, schema["CAS_READS"].index] - stats[0, schema["CAS_READS"].index]

    return 64.0*avg/(1024*1024*1024*u.dt*u.nhosts)

class avg_mdcreqs():
  def compute_metric(self, u):
    schema, _stats = u.get_type("mdc")
    idx = schema["reqs"].index
    avg = 0
    for hostname, stats in _stats.items():
      avg += stats[-1, idx] - stats[0, idx]
    return avg/(u.dt*u.nhosts)

class avg_mdcwait():
  def compute_metric(self, u):
    schema, _stats = u.get_type("mdc")
    idx0, idx1 = schema["reqs"].index, schema["wait"].index
    avg0, avg1 = 0, 0 
    for hostname, stats in _stats.items():
      avg0 += stats[-1, idx0] - stats[0, idx0]
      avg1 += stats[-1, idx1] - stats[0, idx1]
    return avg1/avg0

class avg_openclose():
  def compute_metric(self, u):
    schema, _stats = u.get_type("llite")
    idx0, idx1 = schema["open"].index, schema["close"].index
    avg = 0
    for hostname, stats in _stats.items():
      avg += stats[-1, idx0] - stats[0, idx0] + \
             stats[-1, idx1] - stats[0, idx1]
    return avg/(u.dt*u.nhosts)

class avg_oscreqs():
  def compute_metric(self, u):
    schema, _stats = u.get_type("osc")
    idx = schema["reqs"].index
    avg = 0
    for hostname, stats in _stats.items():
      avg += stats[-1, idx] - stats[0, idx]
    return avg/(u.dt*u.nhosts)

class avg_oscwait():
  def compute_metric(self, u):
    schema, _stats = u.get_type("osc")
    idx0, idx1 = schema["reqs"].index, schema["wait"].index
    avg0, avg1 = 0, 0 
    for hostname, stats in _stats.items():
      avg0 += stats[-1, idx0] - stats[0, idx0]
      avg1 += stats[-1, idx1] - stats[0, idx1]
    return avg1/avg0

class avg_packetsize():
  def compute_metric(self, u):
    try:
      schema, _stats = u.get_type("ib_ext")              
      tx, rx = schema["port_xmit_pkts"].index, schema["port_rcv_pkts"].index
      tb, rb = schema["port_xmit_data"].index, schema["port_rcv_data"].index
      conv2mb = 1024*1024
    except:
      schema, _stats = u.get_type("opa")  
      tx, rx = schema["PortXmitPkts"].index, schema["PortRcvPkts"].index
      tb, rb = schema["PortXmitData"].index, schema["PortRcvData"].index
      conv2mb = 125000

    npacks = 0
    nbytes  = 0
    for hostname, stats in _stats.items():
      npacks += stats[-1, tx] + stats[-1, rx] - \
                stats[0, tx] - stats[0, rx]
      nbytes += stats[-1, tb] + stats[-1, rb] - \
                stats[0, tb] - stats[0, rb]
    return nbytes/(npacks*conv2mb)

class max_fabricbw():
    def compute_metric(self, u):
        max_bw=0
        try:
            schema, _stats = u.get_type("ib_ext")              
            tx, rx = schema["port_xmit_data"].index, schema["port_rcv_data"].index
            conv2mb = 1024*1024
        except:
            schema, _stats = u.get_type("opa")  
            tx, rx = schema["PortXmitData"].index, schema["PortRcvData"].index
            conv2mb = 125000
        for hostname, stats in _stats.items():
            max_bw = max(max_bw, amax(diff(stats[:, tx] + stats[:, rx])/diff(u.t)))
        return max_bw/conv2mb

class max_lnetbw():
    def compute_metric(self, u):
        max_bw=0.0
        schema, _stats = u.get_type("lnet")              
        tx, rx = schema["tx_bytes"].index, schema["rx_bytes"].index
        for hostname, stats in _stats.items():
            max_bw = max(max_bw, amax(diff(stats[:, tx] + stats[:, rx])/diff(u.t)))
        return max_bw/(1024*1024)

class max_mds():
  def compute_metric(self, u):
    max_mds = 0
    schema, _stats = u.get_type("llite")  
    for hostname, stats in _stats.items():
      max_mds = max(max_mds, amax(diff(stats[:, schema["open"].index] + \
                                       stats[:, schema["close"].index] + \
                                       stats[:, schema["mmap"].index] + \
                                       stats[:, schema["fsync"].index] + \
                                       stats[:, schema["setattr"].index] + \
                                       stats[:, schema["truncate"].index] + \
                                       stats[:, schema["flock"].index] + \
                                       stats[:, schema["getattr"].index] + \
                                       stats[:, schema["statfs"].index] + \
                                       stats[:, schema["alloc_inode"].index] + \
                                       stats[:, schema["setxattr"].index] + \
                                       stats[:, schema["listxattr"].index] + \
                                       stats[:, schema["removexattr"].index] + \
                                       stats[:, schema["readdir"].index] + \
                                       stats[:, schema["create"].index] + \
                                       stats[:, schema["lookup"].index] + \
                                       stats[:, schema["link"].index] + \
                                       stats[:, schema["unlink"].index] + \
                                       stats[:, schema["symlink"].index] + \
                                       stats[:, schema["mkdir"].index] + \
                                       stats[:, schema["rmdir"].index] + \
                                       stats[:, schema["mknod"].index] + \
                                       stats[:, schema["rename"].index])/diff(u.t)))
    return max_mds

class max_packetrate():
    def compute_metric(self, u):
        max_pr=0
        try:
            schema, _stats = u.get_type("ib_ext")              
            tx, rx = schema["port_xmit_pkts"].index, schema["port_rcv_pkts"].index
        except:
            schema, _stats = u.get_type("opa")  
            tx, rx = schema["PortXmitPkts"].index, schema["PortRcvPkts"].index

        for hostname, stats in _stats.items():
            max_pr = max(max_pr, amax(diff(stats[:, tx] + stats[:, rx])/diff(u.t)))
        return max_pr

# This will compute the maximum memory usage recorded
# by monitor.  It only samples at x mn intervals and
# may miss high water marks in between.
class mem_hwm():    
  def compute_metric(self, u):
    # mem usage in GB
    max_memusage = 0.0 
    schema, _stats = u.get_type("mem")
    for hostname, stats in _stats.items():
      max_memusage = max(max_memusage, 
                         amax(stats[:, schema["MemUsed"].index] - \
                              stats[:, schema["Slab"].index] - \
                              stats[:, schema["FilePages"].index]))
    return max_memusage/(2.**30)

class node_imbalance():
  def compute_metric(self, u):
    schema, _stats = u.get_type("cpu")
    max_usage = zeros(u.nt - 1)
    for hostname, stats in _stats.items():
      max_usage = maximum(max_usage, diff(stats[:, schema["user"].index])/diff(u.t))

    max_imbalance = []
    for hostname, stats in _stats.items():
      max_imbalance += [mean((max_usage - diff(stats[:, schema["user"].index])/diff(u.t))/max_usage)]    
    return amax([0. if isnan(x) else x for x in max_imbalance])

class time_imbalance():
  def compute_metric(self, u):
    tmid=(u.t[:-1] + u.t[1:])/2.0
    dt = diff(u.t)
    schema, _stats = u.get_type("cpu")    
    vals = []
    for hostname, stats in _stats.items():
      #skip first and last two time slices
      for i in [x + 2 for x in range(len(u.t) - 4)]:
        r1=range(i)
        r2=[x + i for x in range(len(dt) - i)]
        rate = diff(stats[:, schema["user"].index])/diff(u.t)
        # integral before time slice 
        a = trapz(rate[r1], tmid[r1])/(tmid[i] - tmid[0])
        # integral after time slice
        b = trapz(rate[r2], tmid[r2])/(tmid[-1] - tmid[i])
        # ratio of integral after time over before time
        vals += [b/a]        
    if vals:
      return min(vals)
    else:
      return None

class vecpercent_64b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"SSE_D_ALL" : 1, "SIMD_D_256" : 2, 
                    "FP_ARITH_INST_RETIRED_SCALAR_DOUBLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE" : 2, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE" : 4, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE" : 8, 
                     "SSE_DOUBLE_SCALAR" : 1, 
                     "SSE_DOUBLE_PACKED" : 2, 
                     "SIMD_DOUBLE_256" : 4}
    vector_flops = 0.0
    scalar_flops = 0.0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths.keys():
          index = schema[eventname].index
          flops = (stats[-1, index] - stats[0, index])*vector_widths[eventname]
          if vector_widths[eventname] > 1: vector_flops += flops
          else: scalar_flops += flops
    return 100*vector_flops/(scalar_flops + vector_flops)

class avg_vector_width_64b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"SSE_D_ALL" : 1, "SIMD_D_256" : 2, 
                    "FP_ARITH_INST_RETIRED_SCALAR_DOUBLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE" : 2, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE" : 4, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE" : 8, 
                     "SSE_DOUBLE_SCALAR" : 1, 
                     "SSE_DOUBLE_PACKED" : 2, 
                     "SIMD_DOUBLE_256" : 4}
    flops = 0.0
    instr = 0.0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths.keys():
          index = schema[eventname].index
          instr += (stats[-1, index] - stats[0, index])
          flops += (stats[-1, index] - stats[0, index])*vector_widths[eventname]
    return flops/instr

class vecpercent_32b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"FP_ARITH_INST_RETIRED_SCALAR_SINGLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_SINGLE" : 4, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_SINGLE" : 8, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_SINGLE" : 16}
    vector_flops = 0.0
    scalar_flops = 0.0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths.keys():
          index = schema[eventname].index
          flops = (stats[-1, index] - stats[0, index])*vector_widths[eventname]
          if vector_widths[eventname] > 1: vector_flops += flops
          else: scalar_flops += flops
    return 100*vector_flops/(scalar_flops + vector_flops)

class avg_vector_width_32b():
  def compute_metric(self, u):
    schema, _stats = u.get_type("pmc")
    vector_widths = {"FP_ARITH_INST_RETIRED_SCALAR_SINGLE" : 1, 
                     "FP_ARITH_INST_RETIRED_128B_PACKED_SINGLE" : 4, 
                     "FP_ARITH_INST_RETIRED_256B_PACKED_SINGLE" : 8, 
                     "FP_ARITH_INST_RETIRED_512B_PACKED_SINGLE" : 16}
    flops = 0.0
    instr = 0.0
    for hostname, stats in _stats.items():
      for eventname in schema:
        if eventname in vector_widths.keys():
          index = schema[eventname].index
          instr += (stats[-1, index] - stats[0, index])
          flops += (stats[-1, index] - stats[0, index])*vector_widths[eventname]
    return flops/instr


class avg_sf_evictrate():
  def compute_metric(self, u):
    schema, _stats = u.get_type("cha")
    sf_evictions = 0
    llc_lookup = 0                  
    for hostname, stats in _stats.items():
      sf_evictions += stats[-1, schema["SF_EVICTIONS_MES"].index] - \
                      stats[0, schema["SF_EVICTIONS_MES"].index]
      llc_lookup   += stats[-1, schema["LLC_LOOKUP_DATA_READ_LOCAL"].index] - \
                      stats[0, schema["LLC_LOOKUP_DATA_READ_LOCAL"].index] 
    return sf_evictions/llc_lookup

class avg_page_hitrate():
  def compute_metric(self, u):
    schema, _stats = u.get_type("imc")
    act = 0
    cas = 0                  
    for hostname, stats in _stats.items():
      act += stats[-1, schema["ACT_COUNT"].index] - \
             stats[0, schema["ACT_COUNT"].index]
      cas += stats[-1, schema["CAS_READS"].index] + stats[-1, schema["CAS_WRITES"].index] - \
             stats[0, schema["CAS_READS"].index] - stats[0, schema["CAS_WRITES"].index]
    return (cas - act) / cas

class max_sf_evictrate():
  def compute_metric(self, u):
    schema, _stats = u.get_type("cha", aggregate = False)
    max_rate = 0
    for hostname, dev in _stats.items():    
      sf_evictions = {}
      llc_lookup = {}
      for devname, stats in dev.items():
        socket = devname.split('/')[0]
        sf_evictions.setdefault(socket, 0)
        sf_evictions[socket] += stats[-1, schema["SF_EVICTIONS_MES"].index] - \
                                stats[0, schema["SF_EVICTIONS_MES"].index]
        llc_lookup.setdefault(socket, 0)
        llc_lookup[socket]   += stats[-1, schema["LLC_LOOKUP_DATA_READ_LOCAL"].index] - \
                                stats[0, schema["LLC_LOOKUP_DATA_READ_LOCAL"].index]

      for socket in set([x.split('/')[0] for x in dev.keys()]):
        max_rate = max(sf_evictions[socket]/llc_lookup[socket], max_rate)
    return max_rate

class max_load15():    
  def compute_metric(self, u):
    max_load15 = 0.0 
    schema, _stats = u.get_type("ps")
    for hostname, stats in _stats.items():
      max_load15 = max(max_load15, amax(stats[:, schema["load_15"].index]))
    return max_load15/100
