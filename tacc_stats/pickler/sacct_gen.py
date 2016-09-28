import os, sys
from datetime import timedelta, date, datetime
from dateutil.parser import parse
from tacc_stats import cfg

acct_path = cfg.acct_path

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)
try:
    start_date = parse(sys.argv[1])
except:
    start_date = datetime.now()

try:
    end_date   = parse(sys.argv[2])
except:
    end_date = start_date + timedelta(1)

for single_date in daterange(start_date, end_date):

    file_name = os.path.join(acct_path, single_date.strftime("%Y-%m-%d")) + ".txt"
    os.system("/opt/slurm/default/bin/sacct -a -s CA,CD,F,NF,TO -P -X -S " + single_date.strftime("%Y-%m-%d") + " -E " + (single_date + timedelta(1)).strftime("%Y-%m-%d") +" -o JobID,User,Account,Start,End,Submit,Partition,TimeLimit,JobName,State,NNodes,ReqCPUS,NodeList > " + file_name)

