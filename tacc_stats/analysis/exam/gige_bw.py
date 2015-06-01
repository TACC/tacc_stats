from exams import Test
import numpy

class GigEBW(Test):
    k1 = ['net', 'net'] 
    
    k2 = ['rx_bytes', 'tx_bytes']
    
    comp_operator='>'
    aggregate = False

    def compute_metric(self):
        
        data = {}
        try:
            for hostn,host in self.ts.j.hosts.iteritems():
                data[hostn] = [host.get_stats('net','eth0','rx_bytes')+host.get_stats('net','eth0','tx_bytes')]
        except:
            for hostn,host in self.ts.j.hosts.iteritems():
                data[hostn] = [host.get_stats('net','eth1','rx_bytes')+host.get_stats('net','eth1','tx_bytes')]

        self.metric = self.arc(data)
        return
