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
        try:
            del job.acct['yesno'], job.acct['unknown']
        except: pass

        field = job.acct
        field['path'] = pickle_path
        
        field['start_epoch'] = field['start_time']
        field['end_epoch'] = field['end_time']

        utc_start = datetime.utcfromtimestamp(field['start_time']).replace(tzinfo=pytz.utc)
        utc_end = datetime.utcfromtimestamp(field['end_time']).replace(tzinfo=pytz.utc)
        tz = pytz.timezone('US/Central')
        
        field['start_time'] = utc_start.astimezone(tz) 
        field['end_time'] =  utc_end.astimezone(tz)

        field['date'] = field['end_time'].date()

        self.json[field['id']] = field

    def load_dict(self):

        try: 
            with open(self.meta_path, 'rb') as f:
                meta_dict = pickle.load(f)          
            # Get the correct dirs for this sytem
            meta_dict['pickle_dir'] = self.pickle_dir
            meta_dict['meta_path'] = self.meta_path
            meta_dict['directory'] = self.directory

            self.__dict__.update(meta_dict)
            print 'Use old json for meta data but update if necessary'
        except: 
            print 'Build new json for meta data'

    def load_update(self):

        files = os.listdir(self.pickle_dir)
        
        self.load_dict()
        ctr = 0

        for pickle_file in files:
            if pickle_file in self.json: continue
            try:
                pickle_path = os.path.join(self.pickle_dir,pickle_file) 
                with open(pickle_path, 'rb') as fh:
                    data = pickle.load(fh)
                    self.add_job(data, pickle_path)
                ctr = ctr + 1
            except: 
                if os.path.join(self.pickle_dir,pickle_file) == self.meta_path: pass
                else: 
                    print "Pass over ",pickle_file,": it doesn't appear to contain a job object." 
                
            if ctr % 1000 == 0:
                with open(self.meta_path, 'wb') as f:
                    pickle.dump(self.__dict__,f,pickle_prot)

                self.load_dict()
                ctr = 0

        with open(self.meta_path, 'wb') as f:
            pickle.dump(self.__dict__,f,pickle_prot)

