import csv, os, subprocess, datetime, time

# This file is for the SLRUM scheduler that is installed on Rush.ccr.buffalo.edu
# The accounting files are updated nightly with COMPLETED jobs.

# Accounting file header:
# jobid,cluster,partition,account,group,user,submit,eligible,start,end,exitcode,nnodes,ncpus,nodelist,jobname

stats_home = os.getenv('TACC_STATS_HOME', '/scratch/projects/tacc_stats')
acct_path = os.getenv('TACC_STATS_ACCT', os.path.join(stats_home, 'accounting'))

fields = (
    ('id',                          int, 'Job identifier'),
    ('cluster',                     str, 'Job cluster'),
    ('partition',                   str, 'Job partition'),
    ('account',                     str, 'Job account'),
    ('group',                       str, 'Group name of the job owner'),
    ('user',                        str, 'User that is running the job'),
    ('submit',                      int, 'Time the job was submitted'),
    ('eligible',                    int, 'Time job was eligible to run (unix time stamp)'),
    ('start_time',                  int, 'Time job started to run (unix time stamp)'),
    ('end_time',                    int, 'Time job ended (unix time stamp)'),
    ('exit_code',                   str, 'Exit status of job'),
    ('nnodes',                      int, 'Number of nodes'),
    ('ncpus',                       int, 'Number of cpus'),
    ('node_list',                   str, 'Nodes used in job'),
    ('jobname',                     str, 'Job name')
)


# reader(dir, start_time=0, end_time=9223372036854775807L):
#  Info:
#   Reads in SLURM accounting files and searches for jobs that have ended
#   between the specified dates.
#  Inputs:
#   dir - directory where slurm accounting files are located
#   start_time - look for jobs starting at this date
#   end_time - look for jobs ending at this time
#  Returns:
#   Iterator for all jobs that finished between start_time and end_time, the
#   iterator is returned with the yield command so it will use less memory.
def reader(dir, start_time=0, end_time=9223372036854775807L):

    # turn unix timestamp into date object
    start_date = datetime.date.fromtimestamp(start_time)
    end_date = datetime.date.fromtimestamp(end_time)

    # loop through all dates specified
    while ( start_date <= end_date ):

        # open accounting file
        acct_record_file = open( os.path.join( dir, start_date.strftime('%Y%m%d') ), 'r')

        # loop through records in accounting file
        for acct_record in acct_record_file:

            acct_data = acct_record.split('|')
            acct_data_dict = dict(zip([tup[0] for tup in fields],acct_data))

            # convert time to unix timestamp
            for t in ['start_time', 'end_time', 'eligible', 'submit']:
                tmp = time.strptime(acct_data_dict[t],'%Y-%m-%dT%H:%M:%S')
                acct_data_dict[t] = time.strftime("%s",tmp)

            # convert data types in array
            try:
                for stat_name, stat_type, stat_desc in fields:
                    acct_data_dict[stat_name] = stat_type(acct_data_dict[stat_name])
            except:
                pass

            if start_time <= d['end_time'] and d['end_time'] < end_time 
                yield acct_data_dict

        start_date += datetime.timedelta(days=1)


def from_id_with_file_1(id, acct_file):
    for acct in reader(acct_file):
        if acct['id'] == id:
            return acct
        return None


def from_id_with_file(id, acct_file, **kwargs):
    """from_id_with_file(id, acct_file, use_awk=True)
    Return SGE accounting data for the job with SGE ID id from acct_file,
    or None if no such data was found.
    """
    id = str(id)
    if kwargs.get('use_awk', True):
        # Use awk to filter accounting file (2s with, 100s without).
        prog = '$6 == "%s" && $42 == "NONE" { print $0; exit 0; }' % id
        pipe = subprocess.Popen(['/bin/awk', '-F:', prog],
                                bufsize=-1,
                                stdin=acct_file,
                                stdout=subprocess.PIPE)
        try:
            return from_id_with_file_1(id, pipe.stdout)
        finally:
            if pipe.poll() is None:
                pipe.kill()
                pipe.wait()
    else:
        return from_id_with_file_1(id, acct_file)


def from_id(id, **kwargs):
    """from_id(id, acct_file=None, acct_path=acct_path, use_awk=True)
    Return SGE accounting data for the job with SGE ID id from acct_file
    or acct_path.
    """
    acct_file = kwargs.get('acct_file')
    if acct_file:
        return acct_from_id_with_file(id, acct_file, **kwargs)
    else:
        with open(kwargs.get('acct_path', acct_path)) as acct_file:
            return from_id_with_file(id, acct_file, **kwargs)


def fill_with_file_1(id_dict, acct_file):
    for acct in reader(acct_file):
        if acct['id'] in id_dict:
            id_dict[acct['id']] = acct


def fill_with_file(id_dict, acct_file, **kwargs):
    """fill_with_file(id_dict, acct_file, use_awk=True)
    Fill SGE accounting data for the jobs with SGE ids in id_dict from acct_file.
    The keys of id_dict must be strings.
    """
    if kwargs.get('use_awk', True):
        # Use awk to filter accounting file (2s with, 100s without).
        a_defs = ''
        for id in id_dict:
            a_defs += 'a["%s"] = 1;' % id
        prog = 'BEGIN { %s } $6 in a && $42 == "NONE" { print $0; }' % a_defs
        pipe = subprocess.Popen(['/bin/awk', '-F:', prog],
                                bufsize=-1,
                                stdin=acct_file,
                                stdout=subprocess.PIPE)
        try:
            return fill_with_file_1(id_dict, pipe.stdout)
        finally:
            if pipe.poll() is None:
                pipe.kill()
                pipe.wait()
    else:
        return fill_with_file_1(id_dict, acct_file)


def fill(id_dict, **kwargs):
    """fill(id_dict, acct_file=None, acct_path=acct_path, use_awk=True)
    Fill SGE accounting data for the jobs with SGE ids in id_dict from acct_file.
    The keys of id_dict must be strings.
    """
    acct_file = kwargs.get('acct_file')
    if acct_file:
        return fill_with_file(id_dict, acct_file, **kwargs)
    else:
        with open(kwargs.get('acct_path', acct_path)) as acct_file:
            return fill_with_file(id_dict, acct_file, **kwargs)
