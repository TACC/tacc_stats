from exams import Test
import numpy,math

class PacketSize(Test):
  k1=['ib_sw','ib_sw',
      'ib_sw','ib_sw']
  k2=['rx_packets','tx_packets',
      'rx_bytes', 'tx_bytes']

  comp_operator='<'

  def compute_metric(self):

    rx_mean_size=0.
    tx_mean_size=0.
  
    for h in self.ts.j.hosts.keys():
      rx_packet_rate=numpy.diff(self.ts.data[0][h])/numpy.diff(self.ts.t)
      tx_packet_rate=numpy.diff(self.ts.data[1][h])/numpy.diff(self.ts.t)

      rx_bytes_rate=numpy.diff(self.ts.data[2][h])/numpy.diff(self.ts.t)
      tx_bytes_rate=numpy.diff(self.ts.data[3][h])/numpy.diff(self.ts.t)

      rx_packet_size=rx_bytes_rate/rx_packet_rate
      tx_packet_size=tx_bytes_rate/tx_packet_rate

      rx_mean_size+=rx_packet_size
      tx_mean_size+=tx_packet_size

    rx_mean_size/=len(self.ts.j.hosts.keys())
    tx_mean_size/=len(self.ts.j.hosts.keys())

    metric=numpy.mean((rx_mean_size+tx_mean_size)/2.0)

    

    self.metric=metric
    

    return
