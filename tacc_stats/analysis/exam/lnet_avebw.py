from exams import Test
import numpy

class LnetAveBW(Test):
    k1 = ['lnet', 'lnet']     
    k2 = ['rx_bytes', 'tx_bytes']
    
    def compute_metric(self):
        self.metric = self.arc(self.ts.data[0]) + self.arc(self.ts.data[1])
        return
