from exams import Test

class GigEPacketSize(Test):
  k1=['eth0','eth0','eth0','eth0']
  k2=['rx_packets','tx_packets',
      'rx_bytes', 'tx_bytes']

  comp_operator='<'

  def compute_metric(self):

    rx_mean_size = self.arc(self.ts.data[2])/self.arc(self.ts.data[0])
    tx_mean_size = self.arc(self.ts.data[3])/self.arc(self.ts.data[1])
    self.metric=(rx_mean_size+tx_mean_size)/2.0
    
    return
