from plots import Plot
from tacc_stats.analysis.gen import tspl_utils
from matplotlib.figure import Figure
import numpy 

class MasterPlot(Plot):
  k1={'amd64' :
      ['amd64_core','amd64_core','amd64_sock','lnet','lnet',
       'ib_sw','ib_sw','cpu'],
      'intel_pmc3' : ['intel_pmc3', 'intel_pmc3', 'intel_pmc3', 'intel_pmc3',
                      'lnet', 'lnet', 'ib_ext','ib_ext','cpu','mem','mem','mem'],
      'intel_nhm' : ['intel_nhm', 'intel_nhm', 'intel_nhm', 'intel_nhm', 
                     'lnet', 'lnet', 'ib_ext','ib_ext','cpu','mem','mem','mem'],
      'intel_wtm' : ['intel_wtm', 'intel_wtm', 'intel_wtm', 'intel_wtm', 
                     'lnet', 'lnet', 'ib_ext','ib_ext','cpu','mem','mem','mem'],
      'intel_snb' : ['intel_snb_imc', 'intel_snb_imc', 'intel_snb', 
                     'lnet', 'lnet', 'ib_sw','ib_sw','cpu',
                     'intel_snb', 'intel_snb', 'intel_snb', 'mem', 'mem','mem'],
      'intel_hsw' : ['intel_hsw_imc', 'intel_hsw_imc', 'intel_hsw', 
                     'lnet', 'lnet', 'ib_sw','ib_sw','cpu',
                     'intel_hsw', 'intel_hsw', 'intel_hsw', 'mem', 'mem','mem'],

      }
  
  k2={'amd64':
      ['SSE_FLOPS','DCSF','DRAM','rx_bytes','tx_bytes',
       'rx_bytes','tx_bytes','user'],
      'intel_pmc3' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                      'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                      'FP_COMP_OPS_EXE_SSE_PACKED',
                      'FP_COMP_OPS_EXE_SSE_SCALAR',
                      'rx_bytes','tx_bytes', 
                      'port_recv_data','port_xmit_data','user', 'MemUsed', 
                      'FilePages','Slab'],
      'intel_nhm' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                     'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                     'FP_COMP_OPS_EXE_SSE_PACKED',
                     'FP_COMP_OPS_EXE_SSE_SCALAR', 
                     'rx_bytes','tx_bytes', 
                     'port_recv_data','port_xmit_data','user', 'MemUsed', 
                     'FilePages','Slab'],
      'intel_wtm' : ['MEM_UNCORE_RETIRED_REMOTE_DRAM',
                     'MEM_UNCORE_RETIRED_LOCAL_DRAM',
                     'FP_COMP_OPS_EXE_SSE_PACKED',
                     'FP_COMP_OPS_EXE_SSE_SCALAR', 
                     'rx_bytes','tx_bytes', 
                     'port_recv_data','port_xmit_data','user', 'MemUsed', 
                     'FilePages','Slab'],
      'intel_snb' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user',
                     'SSE_DOUBLE_SCALAR', 'SSE_DOUBLE_PACKED', 
                     'SIMD_DOUBLE_256', 'MemUsed', 'FilePages','Slab'],
      'intel_hsw' : ['CAS_READS', 'CAS_WRITES', 'LOAD_L1D_ALL',
                     'rx_bytes','tx_bytes', 'rx_bytes','tx_bytes','user',
                     'SSE_DOUBLE_SCALAR', 'SSE_DOUBLE_PACKED', 
                     'SIMD_DOUBLE_256', 'MemUsed', 'FilePages','Slab'],

      }

  fname='master'

  def plot(self,jobid,job_data=None):
    if not self.setup(jobid,job_data=job_data): return
    wayness=self.ts.wayness
    if self.lariat_data != 'pass':
      if self.lariat_data.wayness and self.lariat_data.wayness < self.ts.wayness:
        wayness=self.lariat_data.wayness
    
    if self.wide:
      self.fig = Figure(figsize=(15.5,12),dpi=110)
      self.ax=self.fig.add_subplot(6,2,2)
      cols = 2
      shift = 2
    else:
      self.fig = Figure(figsize=(8,12),dpi=110)
      self.ax=self.fig.add_subplot(6,1,1)
      cols = 1
      shift = 1
    if self.mode == 'hist':
      plot=self.plot_thist
    elif self.mode == 'percentile':
      plot=self.plot_mmm
    else:
      plot=self.plot_lines

    k1_tmp=self.k1[self.ts.pmc_type]
    k2_tmp=self.k2[self.ts.pmc_type]

    # Plot key 1 for flops
    ax = self.fig.add_subplot(6,cols,1*shift)
    schema = self.ts.j.get_schema(self.ts.pmc_type)

    for host_name in self.ts.j.hosts.keys():
      stats = self.ts.j.aggregate_stats(self.ts.pmc_type,host_names=[host_name])
      if self.ts.pmc_type == 'intel_snb' :    
        if 'SSE_D_ALL' in schema:
          flops = stats[0][:,schema['SSE_D_ALL'].index]+4*stats[0][:,schema['SIMD_D_256'].index]          
        elif 'SSE_DOUBLE_SCALAR' in schema:
          flops = stats[0][:,schema['SSE_DOUBLE_SCALAR'].index]+2*stats[0][:,schema['SSE_DOUBLE_PACKED'].index]+4*stats[0][:,schema['SIMD_DOUBLE_256'].index]          
        else: print("FLOP stats not available for JOBID",self.ts.j.id)
      elif self.ts.pmc_type == 'intel_pmc3' or self.ts.pmc_type == 'intel_nhm' or self.ts.pmc_type == 'intel_wtm':
        if 'FP_COMP_OPS_EXE_SSE_PACKED' in schema and 'FP_COMP_OPS_EXE_SSE_SCALAR' in schema:
          flops = 2*stats[0][:,schema['FP_COMP_OPS_EXE_SSE_PACKED'].index]+stats[0][:,schema['FP_COMP_OPS_EXE_SSE_SCALAR'].index]
        else: print("FLOP stats not available for JOBID",self.ts.j.id)
      elif self.ts.pmc_type == 'intel_hsw' :
        print('Haswell does not support FLOP counters')
      else: 
        print(self.ts.pmc_type + ' not currently supported')
        continue

      try:
        flops = numpy.diff(flops)/numpy.diff(self.ts.t)/1.0e9
        ax.step(self.ts.t/3600., numpy.append(flops,[flops[-1]]), where="post")
        ax.set_ylabel('Dbl GFLOPS')
        ax.set_xlim([0.,self.ts.t[-1]/3600.])
        tspl_utils.adjust_yaxis_range(ax,0.1)
      except: print("FLOP plot not available for JOBID",self.ts.j.id)
    # Plot key 2
    if self.ts.pmc_type == 'intel_snb' or self.ts.pmc_type == 'intel_hsw':
      idx0=k2_tmp.index('CAS_READS')
      idx1=k2_tmp.index('CAS_WRITES')
    if self.ts.pmc_type == 'intel_pmc3' or self.ts.pmc_type == 'intel_nhm' or self.ts.pmc_type == 'intel_wtm' :
      idx0=k2_tmp.index('MEM_UNCORE_RETIRED_REMOTE_DRAM')
      idx1=k2_tmp.index('MEM_UNCORE_RETIRED_LOCAL_DRAM')
    try: 
      plot(self.fig.add_subplot(6,cols,2*shift), [idx0,idx1], 3600., 1.0/64.0*1024.*1024.*1024., ylabel='Total Mem BW GB/s')
    except:
      pass
    #Plot key 3
    idx0=k2_tmp.index('MemUsed')
    idx1=k2_tmp.index('FilePages')
    idx2=k2_tmp.index('Slab')

    plot(self.fig.add_subplot(6,cols,3*shift), [idx0,-idx1,-idx2], 3600.,2.**30.0, ylabel='Memory Usage GB',do_rate=False)

    # Plot lnet sum rate
    idx0=k1_tmp.index('lnet')
    idx1=idx0 + k1_tmp[idx0+1:].index('lnet') + 1
    plot(self.fig.add_subplot(6,cols,4*shift), [idx0,idx1], 3600., 1024.**2, ylabel='Total lnet MB/s')

    # Plot remaining IB sum rate
    if self.ts.pmc_type == 'intel_snb' or self.ts.pmc_type == 'intel_hsw':
      idx2=k1_tmp.index('ib_sw')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_sw') + 1
    if self.ts.pmc_type == 'intel_pmc3' or self.ts.pmc_type == 'intel_nhm' or self.ts.pmc_type == 'intel_wtm':
      idx2=k1_tmp.index('ib_ext')
      idx3=idx2 + k1_tmp[idx2+1:].index('ib_ext') + 1

    plot(self.fig.add_subplot(6,cols,5*shift),[idx2,idx3,-idx0,-idx1],3600.,2.**20,
         ylabel='Total (ib-lnet) MB/s') 

    #Plot CPU user time
    idx0=k2_tmp.index('user')
    plot(self.fig.add_subplot(6,cols,6*shift),[idx0],3600.,wayness*100.,
         xlabel='Time (hr)',
         ylabel='Total cpu user\nfraction')

    self.fig.subplots_adjust(hspace=0.35)
    self.output('master')
