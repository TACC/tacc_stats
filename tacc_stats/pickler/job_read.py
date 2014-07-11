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
                        print self.data.times[t],dev_data[t]
                        old = new

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='print pickle data')

    parser.add_argument('-file', help='Pickle file to read',type=str)
    parser.add_argument('-type', help='Device Type to print',type=str,default=['all'],nargs='*')
    parser.add_argument('-device', help='Device to print',type=str,default=['all'],nargs='*')

    args = parser.parse_args()
    print args
    unpickler = JobRead(args.file)
    
    unpickler.print_data(args.type,args.device)

