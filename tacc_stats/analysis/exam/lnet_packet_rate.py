from exams import Test
import numpy,math

class LnetPacketRate(Test):
  k1=['lnet','lnet', 'cpu']
  k2=['rx_msgs','tx_msgs', 'user']

  comp_operator='>'

  def compute_metric(self):

### Working test for high Lnet packet rate:
###    max_rx=0.
###    max_tx=0.
###
###    for h in self.ts.j.hosts.keys():
###      rx_rate=numpy.diff(self.ts.data[0][h])/numpy.diff(self.ts.t)
###      tx_rate=numpy.diff(self.ts.data[1][h])/numpy.diff(self.ts.t)
###
###      max_rx=max(max_rx,numpy.max(rx_rate))
###      max_tx=max(max_tx,numpy.max(tx_rate))
###
###    self.metric=max(max_rx,max_tx)

    ### UGLY HACK to get combined packet rate and low CPU utilization

    dt=numpy.diff(self.ts.t)

    cpu_thresh=numpy.zeros_like(dt)+0.8
    pack_thresh=numpy.zeros_like(dt)+2000.
    combined=numpy.zeros_like(dt)

    #4005986

    for h in self.ts.j.hosts.keys():
      rx_rate  = numpy.diff(self.ts.data[0][h])/dt
      tx_rate  = numpy.diff(self.ts.data[1][h])/dt
      max_rate = numpy.maximum(rx_rate,tx_rate)
      cpu_frac = numpy.diff(self.ts.data[2][h])/dt/16./1000.

      combined += numpy.logical_and(numpy.greater(max_rate,pack_thresh),numpy.less(cpu_frac,cpu_thresh))[0]
      
    combined /= float(len(self.ts.j.hosts.keys()))
    self.metric=numpy.mean(combined)

    return
