#!/usr/bin/python

# About:
# Inserts summary data from tacc_stats into mongo.
# It removes the '.' from any key in the summary
# json and replaces it with '-'. It then adds new
# date keys from information within the 'acct' key.

# Arguments:
#  argv[1] - directory path to insert data (summary json files)
#            * it can have sub directories
#  argv[2] - machine name

# Example Run:
# python summaryConvertToMongo.py /ifs/projects/xdtas/summaries/rush rush

# Output:
#  stderr - any errors that occur
#  stdout - the name of the file that was inserted into mongo

import sys
import json
import pymongo
import os
import subprocess
import datetime
from pymongo import MongoClient

# Removes any '.' in the json key name and replaces
# it with '-'. We need to do this because mongo does 
# not like '.' in the key names.
def removeDotKey(obj):

    for key in obj.keys():
        new_key = key.replace(".", "-")
        if new_key != key:
            obj[new_key] = obj[key]
            del obj[key]
    return obj

# Returns the json that will be put into mongo from
# the flat summary json file on the fs
def getJson(fpath, machine, nodeinfo):

    try:
        f = open(fpath,'r')
        j = json.loads(f.read(), object_hook=removeDotKey)
    except:
        sys.stderr.write("ERROR in getJson on input %s\n" % fpath)
        sys.stderr.write(sys.exc_info()[0])
        sys.stderr.write("\n\n")
        raise

    # Add extra keys into the json document so that it is easier
    # to search for in mongo, each machine has different names.
    try:
        if machine.lower() == 'rush':
            j["_id"] = machine + '-' + str(j["acct"]["id"])
            j["start_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["start_time"])
            j["end_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["end_time"])
            j["submit_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["submit"])
            j["eligible_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["eligible"])
            # add in the number of cpu's avail to the job
            cpuavail=0
            for host in j["hosts"]:
                cpuavail += nodeinfo.ncpus(host)
            if cpuavail > 0:
                j["acct"]["cpu_avail"] = cpuavail
        if machine.lower() == 'lonestar':
            j["_id"] = machine + '-' + str(j["acct"]["id"])
            j["start_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["start_time"])
            j["end_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["end_time"])
            j["submit_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["submission_time"])
        if machine.lower() == 'stampede':
            j["_id"] = machine + '-' + str(j["acct"]["id"])
            j["start_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["start_time"])
            j["end_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["end_time"])
            j["queue_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["queue_time"])
        if machine.lower() == 'u2':
            j["_id"] = machine + '-' + str(j["acct"]["id"])
            j["start_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["start_time"])
            j["end_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["end_time"])
            j["queue_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["qtime"])
            j["eligible_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["etime"])
            j["created_date"] = datetime.datetime.utcfromtimestamp(j["acct"]["ctime"])
    except:
        sys.stderr.write("ERROR in getJson on json document keys %s\n" % fpath)
        sys.stderr.write(sys.exc_info()[0])
        sys.stderr.write("\n\n")
        raise

    f.close()
    return j

# Finds node cpu info for Rush
class NodeCpuInfo:
    def __init__(self):

        self.nodemap = {}
        self.defaultvalue = 8

        args=[ "ssh", "rush", "sinfo", "-a", "-h", "-o", "\"%o %c\"" ]
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        handles = p.communicate()

        for line in handles[0].split('\n'):
            if len(line) > 0:
                entry = line.split(" ")
                self.nodemap[entry[0]] = int(entry[1])

    def ncpus(self, nodename):
        if nodename in self.nodemap:
            return self.nodemap[nodename]
        else:
            return self.defaultvalue



if __name__ == "__main__":

    # check for correct arguments
    if len(sys.argv) != 3:
        print("%s <summaryDirPath> <machineName>" % sys.argv[0])
        sys.exit(1)
    
    # Connect to mongo on tas-db1
    client = MongoClient()
    db = client.suppremm
    collection = db.summary

    # Get node info only for Rush
    nodeinfo = NodeCpuInfo()
    
    # get/check machine name
    machine = sys.argv[2]
    if machine.lower() not in ['rush','lonestar','stampede','u2']:
        print("Machine %s not supported" % machine)
        sys.exit(1)

    # walk through the directoy given in the command line arguments, go
    # through each file and sub directory looking for '.json' files. 
    # When a json file is found, convert the keys and add new key data
    # and then insert the document into mongo
    rootDir = sys.argv[1]
    for dirName, subdirList, fileList in os.walk(rootDir):
        for fname in fileList:
            if fname.endswith('.json'):
                p = os.path.join(rootDir,dirName,fname)
                try:
                    j = getJson(p,machine,nodeinfo)
                    collection.insert(j)
                    print p
                except:
                    sys.stderr.write("ERROR could not insert %s into mongo\n\n" % p)
