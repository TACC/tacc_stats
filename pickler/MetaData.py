import os, sys
from datetime import datetime
import pytz
import cPickle as pickle
import job_stats
utc = pytz.utc
pickle_prot = pickle.HIGHEST_PROTOCOL

class MetaData():
    
    def __init__(self):
        self.jsons = []    
    
    def add_job(self, job, pickle_path, date):

        del job.acct['yesno'], job.acct['unknown']
        field = job.acct
        field['path'] = pickle_path
        field['date'] = date

        utc_start = datetime.utcfromtimestamp(field['start_time']).replace(tzinfo=pytz.utc)
        utc_end = datetime.utcfromtimestamp(field['end_time']).replace(tzinfo=pytz.utc)
        tz = pytz.timezone('US/Central')

        field['start_time'] = utc_start.astimezone(tz) 
        field['end_time'] =  utc_end.astimezone(tz)
        
        self.jsons.append(job.acct)

    def build_meta_file(self,pickle_dir):
        date = pickle_dir.split('/')[-1]
        for pickle_file in os.listdir(pickle_dir):
            try:
                pickle_path = os.path.join(pickle_dir,pickle_file) 
                with open(pickle_path, 'r') as fh:
                    data = pickle.load(fh)
                    self.add_job(data, pickle_path, date)
            except: 
                print "Skipping file",pickle_file

        meta_path = os.path.join(pickle_dir,'meta_file')
        meta_file = open(meta_path, 'w')
        pickle.dump(self.jsons, meta_file, pickle_prot)    
