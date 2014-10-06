from exams import Test
import numpy

class PacketRate(Test):
    k1=['ib_sw','ib_sw',
        'ib_ext','ib_ext']
    k2=['rx_packets','tx_packets',
        'port_xmit_pkts', 'port_rcv_pkts']
    
    comp_operator='>'
    
    def compute_metric(self):

        max_rx=0.
        max_tx=0.
        
        for h in self.ts.j.hosts.keys():
            rx_rate=numpy.diff(self.ts.data[0][h])/numpy.diff(self.ts.t)
            tx_rate=numpy.diff(self.ts.data[1][h])/numpy.diff(self.ts.t)
            
            ext_rx_rate=numpy.diff(self.ts.data[2][h])/numpy.diff(self.ts.t)
            ext_tx_rate=numpy.diff(self.ts.data[3][h])/numpy.diff(self.ts.t)
            
            max_rx=max(max_rx,min(numpy.max(rx_rate),numpy.max(ext_rx_rate)))
            max_tx=max(max_tx,min(numpy.max(tx_rate),numpy.max(ext_tx_rate)))

        self.metric=max(max_rx,max_tx)

        return
