from exams import Test
import numpy

class InternodeIBAveBW(Test):
    k1 = ['ib_sw', 'ib_sw', 'lnet', 'lnet']     
    k2 = ['rx_bytes', 'tx_bytes', 'rx_bytes', 'tx_bytes']
    
    comp_operator='>'

    def compute_metric(self):
        self.metric = self.arc(self.ts.data[0]) + self.arc(self.ts.data[1]) - self.arc(self.ts.data[2]) - self.arc(self.ts.data[3])
        return
