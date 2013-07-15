import csv, os, subprocess, datetime

stats_home = os.getenv('TACC_STATS_HOME', '/scratch/projects/tacc_stats')
acct_path = os.getenv('TACC_STATS_ACCT', os.path.join(stats_home, 'accounting'))

fields = (
    ('id',                          int, 'Job identifier'),
    ('user',                        str, 'User name of the job owner'),
    ('account',                     str, 'Account under which job is running'),
    ('queue_time')                  int, 'queue time'),
    ('start_time')                  int, 'start time'),
    ('end_time')                    int, 'start time'),
    ('queue')                       str, 'Queue job was in'),
    ('requested_time')              int, 'Requested time for job to run'),
    ('job_name')                    str, 'Job name'),
    ('status')                      str, 'Job status'),
    ('nnodes',                      int, 'Number of nodes'),
    ('ncpus',                       int, 'Number of cpus')
)


# reader(dir, start_time=0, end_time=9223372036854775807L):
#  Info:
#   Reads in SLURM accounting files for stampede and searches for jobs that
#   have ended between the specified dates.
#  Inputs:
#   file - directory where slurm accounting file is located
#   start_time - look for jobs starting at this date
#   end_time - look for jobs ending at this time
#  Returns:
#   Iterator for all jobs that finished between start_time and end_time, the
#   iterator is returned with the yield command so it will use less memory.
def reader(file, start_time=0, end_time=9223372036854775807L):

    # turn unix timestamp into date object
    start_date = datetime.date.fromtimestamp(start_time)
    end_date = datetime.date.fromtimestamp(end_time)
    
    acct_file = open(file)
    for line in acct_file:
        values = line.split(':')
        del values[3] #ignore this field
        keys = ['id','user','account','queue_time','start_time','end_time','queue','requested_time','job_name','status','nnodes','ncpus']
        acct_dict = dict(zip(keys, values))
        acct_dict['id'] = int(acct_dict['id'])
        acct_dict['queue_time'] = int(acct_dict['queue_time'])
        acct_dict['start_time'] = int(acct_dict['start_time'])
        acct_dict['end_time'] = int(acct_dict['end_time'])
        acct_dict['requested_time'] = int(acct_dict['requested_time'])
        acct_dict['nnodes'] = int(acct_dict['nnodes'])
        acct_dict['ncpus'] = int(acct_dict['ncpus'])
        if start_time <= acct_dict['end_time'] and acct_dict['end_time'] < end_time and acct_dict['status'] == 'COMPLETED':
            yield acct_dict


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
