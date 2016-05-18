from exams import Test
import numpy

class LnetAveMsgs(Test):
    k1 = ['lnet', 'lnet']     
    k2 = ['rx_msgs', 'tx_msgs']
    
    comp_operator='>'

    def compute_metric(self):
        self.metric = self.arc(self.ts.data[0]) + self.arc(self.ts.data[1])
        return
