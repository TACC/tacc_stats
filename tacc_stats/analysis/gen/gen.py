import tspl,tspl_utils
import lariat_utils
from analyze_conf import lariat_path

class Data(object):
    
    ts = None
    ld = None

    def __init__(self,jobid,k1,k2,aggregate=True,stats=None):
        ## Build ts and ld object for a job  
        
        self.k1=k1
        self.k2=k2
        self.jobid=jobid
        self.aggregate=aggregate
        
        try:
            if self.aggregate:
                self.ts=tspl.TSPLSum(jobid,self.k1,self.k2,job_data=stats)
            else:
                self.ts=tspl.TSPLBase(jobid,self.k1,self.k2,job_data=stats)
                
            if not self.ld:
                self.ld=lariat_utils.LariatData()
            
            self.ld.get_job(self.ts.j.id,
                            end_epoch=self.ts.j.end_time,
                            daysback=3,
                            directory=lariat_path)
            return
        except tspl.TSPLException as e:
            return
        except EOFError as e:
            print 'End of file found reading: ' + jobid
            return
