from __future__ import print_function
import os, sys
from nose import with_setup
import cPickle as pickle

from tacc_stats.pickler import job_pickles
from tacc_stats.pickler import job_stats, batch_acct
sys.modules['pickler.job_stats'] = job_stats
sys.modules['pickler.batch_acct'] = batch_acct

path = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(path, 'data')

def setup_func():
    a = open(os.path.join(path,"cfg.py"),"w")
    a.write('tacc_stats_home = \"' + data_dir + '\"\n'
            'acct_path = \"'+ data_dir +'/tacc_jobs_completed\"\n'
            'host_list_dir= \"' + data_dir + '\"\n'
            'pickles_dir= \"' + path + '\"\n'
            'host_name_ext= \"platform.extension\"\n'
            'batch_system = \"SLURM\"\n'
            'seek=0\n')
    a.close()

    print("Write cfg.py")

def teardown_func():
    os.remove(os.path.join(path,"cfg.py"))
    try:
        os.remove(os.path.join(path,"cfg.pyc"))
    except: pass
    os.remove(os.path.join(path,'2013-10-01',"1835740"))
    os.rmdir(os.path.join(path,'2013-10-01'))

@with_setup(setup_func, teardown_func)
def test():

    from tacc_stats.pickler.tests import cfg
    pickle_options = { 'processes'       : 1,
                       'start'           : '2013-10-01',
                       'end'             : '2013-10-02',
                       'pickle_dir'      : cfg.pickles_dir,
                       'batch_system'    : cfg.batch_system,
                       'acct_path'       : cfg.acct_path,
                       'tacc_stats_home' : cfg.tacc_stats_home,
                       'host_list_dir'   : cfg.host_list_dir,
                       'host_name_ext'   : cfg.host_name_ext,
                       'seek'            : cfg.seek
                       }

    pickler = job_pickles.JobPickles(**pickle_options)
    pickler.run()
       
    assert os.path.isfile(os.path.join(path,'2013-10-01','1835740')) == True
    print("Pickle file generated.")

    old = pickle.load(open(os.path.join(path,'1835740_ref')))
    new = pickle.load(open(os.path.join(path,'2013-10-01','1835740')))

    assert new.id == old.id
    for i in range(len(old.times)):
        assert new.times[i] == old.times[i]
    for i in range(len(old.hosts.keys())):
        assert old.hosts.keys()[i] == new.hosts.keys()[i]
    print('id, keys, and times match.')

    for host_name, host in old.hosts.iteritems():
        #for i in range(len(host.times)):
        #    assert host.times[i] == new.hosts[host_name].times[i]

        for type_name, type_stats in host.stats.iteritems():
            if type_name =='ib': continue
            for dev_name, dev_stats in type_stats.iteritems():
                for i in range(len(dev_stats)):
                    for j in range(len(dev_stats[i])):

                        if new.hosts[host_name].stats[type_name][dev_name][i][j]-dev_stats[i][j] != 0.0:
                            print(new.times[i],host_name,type_name,dev_name,new.hosts[host_name].stats[type_name][dev_name][i][j],dev_stats[i][j])
                            #continue
                        assert new.hosts[host_name].stats[type_name][dev_name][i][j] == dev_stats[i][j]

@with_setup(setup_func, teardown_func)
def test_ids():
    from tacc_stats.pickler.tests import cfg
    pickle_options = { 'processes'       : 1,
                       'pickle_dir'      : cfg.pickles_dir,
                       'batch_system'    : cfg.batch_system,
                       'acct_path'       : cfg.acct_path,
                       'tacc_stats_home' : cfg.tacc_stats_home,
                       'host_list_dir'   : cfg.host_list_dir,
                       'host_name_ext'   : cfg.host_name_ext,
                       'seek'            : cfg.seek
                       }
    pickler = job_pickles.JobPickles(**pickle_options)
    pickler.run(['1835740'])
       
    assert os.path.isfile(os.path.join(path,'2013-10-01','1835740')) == True
    print("Pickle file generated.")

    old = pickle.load(open(os.path.join(path,'1835740_ref')))
    new = pickle.load(open(os.path.join(path,'2013-10-01','1835740')))

    assert new.id == old.id
    for i in range(len(old.times)):
        assert new.times[i] == old.times[i]
    for i in range(len(old.hosts.keys())):
        assert old.hosts.keys()[i] == new.hosts.keys()[i]
    print('id, keys, and times match.')

    for host_name, host in old.hosts.iteritems():
        #for i in range(len(host.times)):
        #    assert host.times[i] == new.hosts[host_name].times[i]
        
        for type_name, type_stats in host.stats.iteritems():
            if type_name =='ib': continue
            for dev_name, dev_stats in type_stats.iteritems():
                for i in range(len(dev_stats)):
                    for j in range(len(dev_stats[i])):

                        if new.hosts[host_name].stats[type_name][dev_name][i][j]-dev_stats[i][j] != 0.0:
                            print(new.times[i],host_name,type_name,dev_name,new.hosts[host_name].stats[type_name][dev_name][i][j],dev_stats[i][j])
                            #continue
                        assert new.hosts[host_name].stats[type_name][dev_name][i][j] == dev_stats[i][j]
