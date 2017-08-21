from exams import Test
import numpy

class BlockAveBW(Test):
    k1 = ['block', 'block']     
    k2 = ['rd_sectors', 'wr_sectors']
    
    def compute_metric(self):
        self.metric = (self.arc(self.ts.data[0]) + self.arc(self.ts.data[1]))/(1024*1024)
        return
