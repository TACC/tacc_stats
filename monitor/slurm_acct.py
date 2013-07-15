import csv, os, subprocess, datetime

# TORQUE/PBS accounting file
# docs.adaptivecomputing.com/torque/4-1-3/help.htm#topics/9-accounting/accountingRecords.htm

# TORQUE maintains accounting records for batch jobs in the following directory:
#  $TORQUEROOT/server_priv/accounting/<TIMESTAMP>
#  $TORQUEROOT defaults to /usr/spool/PBS and <TIMESTAMP> is in the format: YYYYMMDD.
# These records include events, time stamps, and information on resources requested and used.
# Records for four different event types are produced and are described in the following table:


stats_home = os.getenv('TACC_STATS_HOME', '/scratch/projects/tacc_stats')
acct_path = os.getenv('TACC_STATS_ACCT', os.path.join(stats_home, 'accounting'))

# rush.ccr.buffalo.edu
# sacct --allusers --parsable2 --noheader --allocations --allclusters --format jobid,cluster,partition,account,group,user,submit,eligible,start,end,exitcode,nnodes,ncpus,nodelist,jobname --state COMPLETED,FAILED --starttime 2013-06-20T00:00:00 --endtime 2013-06-21T00:00:00 > out

fields = (
    ('id',                          int, 'Job identifier'),
    ('cluster',                     str, 'Cluster the job is running on'),
    ('partition',                   str, 'Partition the job is running on'),
    ('account',                     str, 'Account under which job is running'),
    ('group',                       str, 'Group name of the job owner'),
    ('user',                        str, 'User name of the job owner'),
    ('submit',                      str, 'Time the job was submitted'),
    ('eligible',                    str, 'Time the job was eligible to run'),
    ('start',                       int, 'Time job started to run (unix time stamp)'),
    ('end',                         int, 'Time job ended (unix time stamp)'),
    ('exit_code'),                   int, 'Exit code of the job'),
    ('nnodes',                      str, 'Number of nodes'),
    ('ncpus',                       str, 'Number of cpus'),
    ('nodelist',                    str, 'List of nodes used'),
    ('jobname',                     str, 'Job name')
)


# reader(dir, start_time=0, end_time=9223372036854775807L):
#  Info:
#   Reads in TORQUE accounting files and searches for jobs that have ended
#   between the specified dates.
#  Inputs:
#   dir - directory where torque accounting files are located
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

            # check if record corresponds to a job ending
            acct_data = acct_record.split(';')
            if acct_data[1] == 'E':

                # put record into associative array
                acct_data_arr = {}
                acct_data_arr['id'] = acct_data[2][:acct_data[2].find('.')]
                acct_data = acct_data[3].split(' ')

                for stat in acct_data:
                    acct_data_arr[ stat[:stat.find('=')] ] = stat[stat.find('=')+1:].strip()

                acct_data_arr['hostname'] = acct_data_arr['exec_host'][:acct_data_arr['exec_host'].find('/')]

                # convert data types in array
                try:
                    for stat_name, stat_type, stat_desc in fields:
                        acct_data_arr[stat_name] = stat_type(acct_data_arr[stat_name])
                except:
                    pass

                # change key names
                acct_data_arr['start_time'] = acct_data_arr['start']
                del acct_data_arr['start']
                acct_data_arr['end_time'] = acct_data_arr['end']
                del acct_data_arr['end']

                # check start and end times then yield job array (yield returns a itterator)
                if start_time <= acct_data_arr['end_time'] and acct_data_arr['end_time'] < end_time:
                    yield acct_data_arr

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
