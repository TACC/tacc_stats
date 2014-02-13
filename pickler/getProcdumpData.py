#!/usr/bin/python
#./getProcdumpData.py /data/scratch/Rush/archive/k13n24s02/20130823.gz 178701
import gzip, sys, time, datetime, os, base64, zlib, StringIO, subprocess
import re

class TaccProcParser:
    def __init__(self):
        self.processes={}

    def __str__(self):
        # Return all of the names of the unique processes
        # If multiple processes have the same name then it will appear
        # multiple times.
        return str(self.processes.values())

    def parse(self,indata):

        (START, STATUS_LEN, STATUS_NAME, CMDLINE_LEN, CMDLINE_NAME) = range(5)

        state = START
        pid = -1

        for line in indata:
            if state == START:
                if "/status" in line:
                    m = re.search("^/proc/([0-9]+)/status", line)
                    if m:
                        pid = m.group(1)
                        state = STATUS_LEN
                        continue
                if "/cmdline" in line:
                    m = re.search("^/proc/([0-9]+)/cmdline", line)
                    if m:
                        pid = m.group(1)
                        state = CMDLINE_LEN
                continue
            if state == STATUS_LEN:
                state = STATUS_NAME
                continue
            if state == STATUS_NAME:
                if pid not in self.processes:
                    self.processes[pid] = line.split()[1]
                state = START
                continue
            if state == CMDLINE_LEN:
                state = CMDLINE_NAME
                continue
            if state == CMDLINE_NAME:
                self.processes[pid] = line.replace("\0", " ").rstrip()
                state = START
                continue


def getProcdumpData( filename, jid ):

    procParser = TaccProcParser()
    lineNum = 0
    cmd = ""
    procDumpData = []
    running = False
    ending = False
    procDumpLines = []
    try:
        with gzip.open(filename) as f:
            for line in f:
                # store line number
                lineNum += 1
                # test if its already running
                if line[0].isdigit():
                    jobs=line.strip().split()[1].split(',')
                    if jid in jobs:
                        running = True
                # test if it is starting
                if line.startswith("% begin"):
                    if line.strip().split()[2] == jid:
                        running = True
                # test if it is ending
                if line.startswith("% end"):
                    if line.strip().split()[2] == jid:
                        ending = True
                # test if its a procdump line and job is running
                if line.startswith("% procdump") and (running or ending):
                    if len(line) > 40:
                        decoded = StringIO.StringIO(base64.b64decode(line[11:]))
                        gzo = gzip.GzipFile(mode="rb",fileobj=decoded)
                        procParser.parse( gzo )
                    if ending:
                        break
    except TypeError as e:
        print e
        pass
    
    return procParser

if __name__ == '__main__':
    print getProcdumpData( sys.argv[1], sys.argv[2] )

