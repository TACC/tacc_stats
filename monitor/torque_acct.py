import csv, os, subprocess

# TORQUE/PBS accounting file
# docs.adaptivecomputing.com/torque/4-1-3/help.htm#topics/9-accounting/accountingRecords.htm

# TORQUE maintains accounting records for batch jobs in the following directory:
#  $TORQUEROOT/server_priv/accounting/<TIMESTAMP>
#  $TORQUEROOT defaults to /usr/spool/PBS and <TIMESTAMP> is in the format: YYYYMMDD.
# These records include events, time stamps, and information on resources requested and used.
# Records for four different event types are produced and are described in the following table:

# RECORD MARKER / TYPE / DESCRIPTION
# A - Abort        Job has been aborted by the server
# C - checkpoing   Job has been checkpointed and held
# D - delete       job has been deleted
# E - exit         Job has exited, either successfully or unsuccessfully
# Q - queue        Job has been submitted/queued
# R - rerun        Attempt to rerun the job has been made
# S - start        Attempt to start the job has been made
# T - restart      Attempt to restart the job (from checkpoint) has been made

# Accounting Variable Descriptions
# ctime            Time job was created
# etime            Time job became eligible to run
# qtime            Time job was queued
# start            Time job started to run

# NOTES
#  - how to figure out end time? current_time - start_time if status == E


stats_home = os.getenv('TACC_STATS_HOME', '/scratch/projects/tacc_stats')
acct_path = os.getenv('TACC_STATS_ACCT', os.path.join(stats_home, 'accounting'))

fields = (
    ('current_date'     str, 'Current date'),
    ('current_time'     str, 'Current time'),
    ('status'           str, 'Job status'),
    ('id'               str, 'Job identifier'),
    ('hostname'         str, 'Name of the execution host'),
    ('user'             str, 'User that is running the job'),
    ('group'            str, 'Group id of the job owner'),
    ('name'             str, 'Job name'),
    ('queue'            str, 'Queue name the job is running on'),
    ('create_time'      int, 'Time job was created (unix time stamp)'),
    ('queue_time'       int, 'Time job was queued (unix time stamp)'),
    ('eligible_time')   int, 'Time job was eligible to run (unix time stamp)'),
    ('start_time')      int, 'Time job started to run (unix time stamp)'),
    ('owner'            str, 'Owner of the job at hostname'),
    ('nodes'            str, 'Nodes assigned to job'),
    ('walltime')        str, 'Walltime requested')
)

field_names = [tup[0] for tup in fields]


def reader(file, start_time=0, end_time=9223372036854775807L, seek=0):
    """reader(file, start_time=0, end_time=9223372036854775807L, seek=0)
    Return an iterator for all jobs that finished between start_time and end_time.
    """
    if type(file) == str:
        file = open(file)
    if seek:
        file.seek(seek, os.SEEK_SET)
    for d in csv.DictReader(file, delimiter=':', fieldnames=field_names):
        try:
            for n, t, x in fields:
                d[n] = t(d[n])
        except:
            pass
        # Accounting records with pe_taskid != NONE are generated for
        # sub_tasks of a tightly integrated job and should be ignored.
        if start_time <= d['end_time'] and d['end_time'] < end_time and d['pe_taskid'] == 'NONE':
            yield d


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
