from exams import Test
import numpy

class InternodeIBMaxBW(Test):
    k1 = ['ib_sw', 'ib_sw', 'lnet', 'lnet']     
    k2 = ['rx_bytes', 'tx_bytes', 'rx_bytes', 'tx_bytes']    
    comp_operator='>'

    def compute_metric(self):
   
        ts = self.ts
        tmid=(ts.t[:-1]+ts.t[1:])/2.0
        ib_bw = numpy.zeros_like(tmid)

        for k in ts.j.hosts.keys():
            ib_bw += numpy.diff(ts.assemble([0,1,-2,-3],k,0))/numpy.diff(ts.t)

        self.metric = numpy.max(ib_bw)
        return
