#!/usr/bin/env python
from tacc_stats.pickler.job_stats import Job
import cPickle as pickle
import argparse

class JobRead:
    data = None
    
    def __init__(self,filename):
        
        with open(filename,'rb') as fd:
            self.data = pickle.load(fd)
        
    def print_data(self,typ,dev):
        print typ,dev
        print self.data.hosts.keys()
        for host_name, host in self.data.hosts.iteritems():
            
            if 'all' in typ: typ_keys = host.stats.keys()
            else: typ_keys = typ
            
            for type_name in typ_keys:
                type_data = host.stats[type_name]
                
                if 'all' in dev: dev_keys = type_data.keys()
                else: dev_keys = dev


                
                for dev_name in dev_keys:                    
                    dev_data = type_data[dev_name]
                    print host_name,type_name,dev_name,dev_data.shape
                    old = dev_data[0]                    
                    for t in range(len(dev_data)):                        
                        new = dev_data[t]
                        flag = False
                        for j in range(len(new)):
                            if new[j] < old[j]: 
                                flag = True 
                                break
                            
                        #if flag:
                        #    print host_name,type_name,dev_name
                        #    print self.data.times[t-1],old
                        #print self.data.times[t],dev_data[t]
                        dt = self.data.times[t]-self.data.times[0]
                        if dt > 0:
                            _data = (2**-30)*(new-old)/dt
                            print dt,_data
                        old = new
                    print type_name,dev_name
        agg_data = self.data.aggregate_stats(typ_keys[0],dev_names=dev_keys)

        i = 0
        from numpy import diff
        print agg_data
        agg_data = diff(agg_data[0])
        times = diff(self.data.times)

        for dt in times:            
            print dt,(2**-30)*(agg_data[i])/dt
            i+=1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='print pickle data')

    parser.add_argument('-file', help='Pickle file to read',type=str)
    parser.add_argument('-type', help='Device Type to print',type=str,default=['all'],nargs='*')
    parser.add_argument('-device', help='Device to print',type=str,default=['all'],nargs='*')

    args = parser.parse_args()
    print args
    unpickler = JobRead(args.file)
    
    unpickler.print_data(args.type,args.device)

