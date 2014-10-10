from exams import Test
import numpy

class GigEPacketRate(Test):
    k1=['eth0','eth0']
    k2=['rx_packets','tx_packets']
    
    comp_operator='>'
    
    def compute_metric(self):

        self.metric = self.arc(self.ts.data[0])+self.arc(self.ts.data[1])

        return
