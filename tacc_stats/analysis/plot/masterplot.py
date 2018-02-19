import sys
from plots import Plot
from tacc_stats.analysis.gen import tspl_utils
from matplotlib.figure import Figure
import numpy 

class MasterPlot(Plot):

  linux_types = ['cpu','cpu','cpu','cpu','cpu','cpu', 'cpu', 
                 'mem','mem','mem']
  linux_stats = ['user', 'system', 'nice', 'idle', 'iowait', 'irq', 'softirq',
                 'MemUsed', 'FilePages','Slab']

  k1={'amd64' :
      ['amd64_core','amd64_core','amd64_sock','lnet','lnet',
       'ib_sw','ib_sw'] + linux_types,
      'intel_pmc3' : ['intel_pmc3', 'intel_pmc3', 'intel_pmc3', 'intel_pmc3',
                      'lnet', 'lnet', 'ib_ext','ib_ext'] + linux_types,
      'intel_nhm' : ['intel_nhm', 'intel_nhm', 'intel_nhm', 'intel_nhm', 
                     'lnet', 'lnet', 'ib_ext','ib_ext'] + linux_types,
      'intel_wtm' : ['intel_wtm', 'intel_wtm', 'intel_wtm', 'intel_wtm', 
                     'lnet', 'lnet', 'ib_ext','ib_ext','cpu','mem','mem','mem'],
      'intel_snb' : ['intel_snb_imc', 'intel_snb_imc', 'intel_snb', 
                     'lnet', 'lnet', 'ib_sw','ib_sw',
                     'intel_snb', 'intel_snb', 'intel_snb', 'intel_snb', 'intel_snb'] + linux_types,
      'intel_hsw' : ['intel_hsw_imc', 'intel_hsw_imc', 'intel_hsw', 'intel_hsw', 'intel_hsw', 
                     'lnet', 'lnet', 'ib_sw','ib_sw'] + linux_types,
      'intel_ivb' : ['intel_ivb_imc', 'intel_ivb_imc', 'intel_ivb', 'intel_ivb', 'intel_ivb', 
                     'lnet', 'lnet', 'ib_sw','ib_sw',
                     'intel_ivb', 'intel_ivb', 'intel_ivb'] + linux_types,
      'intel_bdw' : ['intel_bdw_imc', 'intel_bdw_imc', 'intel_bdw',  'intel_bdw',  'intel_bdw', 
                     'lnet', 'lnet', 'ib_sw','ib_sw',
                     'intel_bdw', 'intel_bdw', 'intel_bdw'] + linux_types,
      'intel_skx' : ['intel_skx', 'intel_skx', 'intel_skx', 'intel_skx', 
                     'intel_skx_imc', 'intel_skx_imc', 
                     'lnet', 'lnet', 'opa', 'opa', 
                     'intel_skx', 'intel_skx'] + linux_types,
      'intel_knl' : ['intel_knl_mc_dclk', 'intel_knl_mc_dclk', 
                     'intel_knl_edc_eclk', 'intel_knl_edc_uclk', 
                     'intel_knl_edc_uclk', 'intel_knl_edc_eclk', 
                     'lnet', 'lnet', 'opa','opa', 
                     'intel_knl', 'intel_knl'] + linux_types

      }

  
  k2={'amd64':
      ['SSE_FLOPS','DCSF','DRAM','rx_bytes','tx_bytes',
       'rx_bytes','tx_bytes'] + linux_stats,
      'intel_pmc3' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                      'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                      'FP_COMP_OPS_EXE_SSE_PACKED',
                      'FP_COMP_OPS_EXE_SSE_SCALAR',
                      'rx_bytes','tx_bytes', 
                      'port_recv_data','port_xmit_data'] + linux_stats,
      'intel_nhm' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                     'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                     'FP_COMP_OPS_EXE_SSE_PACKED',
                     'FP_COMP_OPS_EXE_SSE_SCALAR', 
                     'rx_bytes','tx_bytes', 
                     'port_recv_data','port_xmit_data'] + linux_stats,
      'intel_wtm' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                     'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                     'FP_COMP_OPS_EXE_SSE_PACKED',
                     'FP_COMP_OPS_EXE_SSE_SCALAR', 
                     'rx_bytes','tx_bytes', 
                     'port_recv_data','port_xmit_data'] + linux_stats,
      'intel_snb' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes',
                     'SSE_DOUBLE_SCALAR', 'SSE_DOUBLE_PACKED', 
                     'SIMD_DOUBLE_256', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,
      'intel_hsw' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,
      'intel_bdw' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,
      'intel_ivb' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes',
                     'SSE_DOUBLE_SCALAR', 'SSE_DOUBLE_PACKED', 
                     'SIMD_DOUBLE_256', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,
      'intel_knl' : ['CAS_READS', 'CAS_WRITES', 'RPQ_INSERTS', 
                     'EDC_MISS_CLEAN', 'EDC_MISS_DIRTY',  'WPQ_INSERTS',
                     'rx_bytes','tx_bytes', 'portRcvData','portXmitData', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,
      'intel_skx' : ['FP_ARITH_INST_RETIRED_SCALAR_DOUBLE', 'FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE', 
                     'FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE', 'FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE', 
                     'CAS_READS', 'CAS_WRITES', 
                     'rx_bytes','tx_bytes', 'portRcvData','portXmitData', 
                     'CLOCKS_UNHALTED_CORE', 'CLOCKS_UNHALTED_REF'] + linux_stats,

      }

  fname='master'

  def plot(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return

    if self.wide:
      self.fig = Figure(figsize=(15.5,12),dpi=110)
      self.ax=self.fig.add_subplot(7,2,2)
      cols = 2
      shift = 2
    else:
      self.fig = Figure(figsize=(8,15),dpi=110)
      self.ax=self.fig.add_subplot(7,1,1)
      cols = 1
      shift = 1
    if self.mode == 'hist':
      plot=self.plot_thist
    if self.mode == 'ratio':
      plot=self.plot_ratio
    elif self.mode == 'percentile':
      plot=self.plot_mmm
    else:
      plot=self.plot_lines

    nom_freq = {"intel_snb" : 2.7, "intel_ivb" : 2.8, "intel_hsw" : 2.3, "intel_bdw" : 2.6, "intel_knl" : 1.4, "intel_skx" : 2.1}
    nom_freq = nom_freq[self.ts.pmc_type]

    k1_tmp=self.k1[self.ts.pmc_type]
    k2_tmp=self.k2[self.ts.pmc_type]
    processor_schema = self.ts.j.schemas[self.ts.pmc_type]
    # Plot key 1 for flops
    print("starting plot")
    plot_ctr = 0
    try:
      if 'SSE_D_ALL' in processor_schema and 'SIMD_D_256' in processor_schema:
        idx0 = k2_tmp.index('SSE_D_ALL')
        idx1 = None
        idx2 = k2_tmp.index('SIMD_D_256')
        idx3 = None
      elif 'FP_ARITH_INST_RETIRED_SCALAR_DOUBLE' in processor_schema:
        idx0 = k2_tmp.index('FP_ARITH_INST_RETIRED_SCALAR_DOUBLE') 
        idx1 = k2_tmp.index('FP_ARITH_INST_RETIRED_128B_PACKED_DOUBLE')
        idx2 = k2_tmp.index('FP_ARITH_INST_RETIRED_256B_PACKED_DOUBLE')
        idx3 = k2_tmp.index('FP_ARITH_INST_RETIRED_512B_PACKED_DOUBLE')
      elif 'SSE_DOUBLE_SCALAR' in processor_schema and 'SSE_DOUBLE_PACKED' in processor_schema and 'SIMD_DOUBLE_256' in processor_schema:
        idx0 = k2_tmp.index('SSE_DOUBLE_SCALAR')
        idx1 = k2_tmp.index('SSE_DOUBLE_PACKED')
        idx2 = k2_tmp.index('SIMD_DOUBLE_256')
        idx3 = None
      elif 'FP_COMP_OPS_EXE_SSE_PACKED' in processor_schema and 'FP_COMP_OPS_EXE_SSE_SCALAR' in processor_schema:
        idx0 = k2_tmp.index('FP_COMP_OPS_EXE_SSE_SCALAR')
        idx1 = k2_tmp.index('FP_COMP_OPS_EXE_SSE_PACKED')
        idx2 = None
        idx3 = None
      else: 
        print("FLOP stats not available for JOBID",self.ts.j.id)
        raise
      plot_ctr += 1
      ax = self.fig.add_subplot(7,cols,plot_ctr*shift)      
      for host_name in self.ts.j.hosts.keys():
        flops = 0
        if idx0: flops += 1*self.ts.assemble([idx0],host_name,0)
        if idx1: flops += 2*self.ts.assemble([idx1],host_name,0)
        if idx2: flops += 4*self.ts.assemble([idx2],host_name,0)
        if idx3: flops += 8*self.ts.assemble([idx3],host_name,0)

        flops = numpy.diff(flops)/numpy.diff(self.ts.t)/1.0e9
        ax.step(self.ts.t/3600., numpy.append(flops, [flops[-1]]), 
                where="post")
        
      ax.set_ylabel('Dbl GFLOPS')
      ax.set_xlim([0.,self.ts.t[-1]/3600.])
      tspl_utils.adjust_yaxis_range(ax,0.1)
    except: 
      print sys.exc_info()
      print("FLOP plot not available for JOBID",self.ts.j.id)

    # Plot MCDRAM BW for KNL
    if self.ts.pmc_type == 'intel_knl':
      if "Flat" in self.ts.j.acct["queue"]:               
        idxs = [k2_tmp.index('RPQ_INSERTS'), k2_tmp.index('WPQ_INSERTS')]
      else:
        idxs = [k2_tmp.index('RPQ_INSERTS'), -k2_tmp.index('EDC_MISS_CLEAN'), 
                -k2_tmp.index('EDC_MISS_DIRTY'), k2_tmp.index('WPQ_INSERTS'), -k2_tmp.index('CAS_READS')]
      plot_ctr += 1
      plot(self.fig.add_subplot(7,cols,plot_ctr*shift), idxs, 3600., 
           (2**30.0)/64., ylabel="MCDRAM BW [GB/s]")

    # Plot key 2
    try:
      if 'CAS_READS' in k2_tmp and 'CAS_WRITES' in k2_tmp:
        idxs = [k2_tmp.index('CAS_READS'), k2_tmp.index('CAS_WRITES')]
      elif 'MEM_UNCORE_RETIRED_REMOTE_DRAM' in k2_tmp and 'MEM_UNCORE_RETIRED_LOCAL_DRAM' in k2_tmp:
        idxs = [k2_tmp.index('MEM_UNCORE_RETIRED_REMOTE_DRAM'), k2_tmp.index('MEM_UNCORE_RETIRED_LOCAL_DRAM')]
      plot_ctr += 1
      plot(self.fig.add_subplot(7,cols,plot_ctr*shift), idxs, 3600., 
           1.0/64.0*1024.*1024.*1024., ylabel='DRAM BW [GB/s]')
    except:
      print(self.ts.pmc_type + ' missing Memory Bandwidth plot' + ' for jobid ' + self.ts.j.id )

    #Plot key 3
    idx0=k2_tmp.index('MemUsed')
    idx1=k2_tmp.index('FilePages')
    idx2=k2_tmp.index('Slab')
    plot_ctr += 1
    plot(self.fig.add_subplot(7,cols,plot_ctr*shift), [idx0,-idx1,-idx2], 3600.,2.**30.0, 
         ylabel='Memory Use [GB]',do_rate=False)

    # Plot lnet sum rate
    idx0=k1_tmp.index('lnet')
    idx1=idx0 + k1_tmp[idx0+1:].index('lnet') + 1
    plot_ctr += 1
    plot(self.fig.add_subplot(7,cols,plot_ctr*shift), [idx0,idx1], 3600., 1024.**2, ylabel='Lustre BW [MB/s]')

    # Plot remaining IB sum rate
    if 'ib_ext' in self.ts.j.hosts.values()[0].stats:
      try:
        idx2=k1_tmp.index('ib_sw')
        idx3=idx2 + k1_tmp[idx2+1:].index('ib_sw') + 1
      except:
        idx2=k1_tmp.index('ib_ext')
        idx3=idx2 + k1_tmp[idx2+1:].index('ib_ext') + 1
      try:
        plot_ctr += 1
        plot(self.fig.add_subplot(7,cols,plot_ctr*shift),[idx2,idx3],3600.,2.**20,
             ylabel='IB BW [MB/s]') 
      except: pass
    FLITS_PER_MB = 125000
    if 'opa' in self.ts.j.hosts.values()[0].stats:
        idx2=k2_tmp.index('portXmitData')
        idx3=k2_tmp.index('portRcvData')
        plot_ctr += 1
        plot(self.fig.add_subplot(7,cols,plot_ctr*shift),[idx2,idx3],3600.,FLITS_PER_MB,
             ylabel='OPA BW [MB/s]') 

    #Plot CPU user time
    busy = [k2_tmp.index('user'), k2_tmp.index('system'), k2_tmp.index('nice')]
    idle = [k2_tmp.index('iowait'), k2_tmp.index('idle'), k2_tmp.index('irq'), k2_tmp.index('softirq')]
    plot_ctr += 1

    self.plot_ratio(self.fig.add_subplot(7,cols,plot_ctr*shift), busy, busy + idle, 3600., 0.01,
                    ylabel='Logical Core Use %')

    #Plot CPU Frequency
    cyc = [k2_tmp.index('CLOCKS_UNHALTED_CORE')]
    cyc_ref = [k2_tmp.index('CLOCKS_UNHALTED_REF')]
    plot_ctr += 1

    self.plot_ratio(self.fig.add_subplot(7,cols,plot_ctr*shift), cyc, cyc_ref, 3600., 1/nom_freq,
                    xlabel='Time [hrs]',
                    ylabel='Active Freq [GHz]')
   
    self.fig.subplots_adjust(hspace=0.35)
    self.output('master')
