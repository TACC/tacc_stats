from exams import Test
import numpy

class LnetMaxBW(Test):
    k1 = ['lnet', 'lnet']     
    k2 = ['rx_bytes', 'tx_bytes']    
    comp_operator='>'

    def compute_metric(self):
   
        ts = self.ts
        tmid=(ts.t[:-1]+ts.t[1:])/2.0
        lnet_bw = numpy.zeros_like(tmid)

        for k in ts.j.hosts.keys():
            lnet_bw += numpy.diff(ts.assemble(range(0,len(ts.k1)),k,0))/numpy.diff(ts.t)

        self.metric = numpy.max(lnet_bw)
        return
