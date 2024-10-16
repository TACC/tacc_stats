import os, sys
# Append your local repository path here:
# sys.path.append("/home/sg99/tacc_stats")
from datetime import timedelta, date, datetime
from dateutil.parser import parse
import tacc_stats.conf_parser as cfg

acct_path = cfg.get_accounting_path()

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
    sacct_command = "/bin/sacct -a -s CA,CD,F,NF,TO -P -X -S " + single_date.strftime("%Y-%m-%d") + " -E " + (single_date + timedelta(1)).strftime("%Y-%m-%d") +" -o JobID,User,Account,Start,End,Submit,Partition,TimeLimit,JobName,State,NNodes,ReqCPUS,NodeList > " + file_name  
    print(sacct_command)
    os.system(sacct_command)
