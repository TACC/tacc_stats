import os, sys
from datetime import datetime
import pytz
import cPickle as pickle
import job_stats
import lariat_utils
import analyze_conf

utc = pytz.utc
pickle_prot = pickle.HIGHEST_PROTOCOL

class MetaData():
    
    ## Constructor
    def __init__(self, pickle_dir):
        self.pickle_dir = pickle_dir
        self.directory = self.pickle_dir.split('/')[-1]
        self.meta_path = os.path.join(self.pickle_dir,'meta_file_'+self.directory)
        self.json = {}

    ## Add a job to the meta_data json list
    def add_job(self, job, pickle_path):

        del job.acct['yesno'], job.acct['unknown']
        field = job.acct
        field['path'] = pickle_path

        utc_start = datetime.utcfromtimestamp(field['start_time']).replace(tzinfo=pytz.utc)
        utc_end = datetime.utcfromtimestamp(field['end_time']).replace(tzinfo=pytz.utc)
        tz = pytz.timezone('US/Central')

        field['start_time'] = utc_start.astimezone(tz) 
        field['end_time'] =  utc_end.astimezone(tz)

        field['date'] = field['end_time'].date()

        self.json[field['id']] = field

    def load_update(self):

        try: 
            f = open(self.meta_path, 'rb+')
            meta_dict = pickle.load(f)
            self.__dict__.update(meta_dict)
            print 'Use old json for meta data but update if necessary'
        except: 
            f = open(self.meta_path, 'wb')
            print 'Build new json for meta data'

        for pickle_file in os.listdir(self.pickle_dir):
            if pickle_file in self.json: continue

            try:
                pickle_path = os.path.join(self.pickle_dir,pickle_file) 
                with open(pickle_path, 'rb') as fh:
                    data = pickle.load(fh)
                    self.add_job(data, pickle_path)
            except: 
                if os.path.join(self.pickle_dir,pickle_file) == self.meta_path: pass
                else: print "Pass over ",pickle_file,": it's not a job object." 

        pickle.dump(self.__dict__,f,pickle_prot)
        f.close()

