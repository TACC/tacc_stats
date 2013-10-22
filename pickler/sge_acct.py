import csv, os, subprocess

# Fields in the sge accounting file.
# From /opt/sge6.2/man/man5/accounting.5

fields = (
    ('queue',           str, 'Name of the cluster queue in which the job has run.'), # sge 'qname'
    ('hostname',        str, 'Name of the execution host.'),
    ('group',           str, 'The effective group id of the job owner when executing the job.'),
    ('owner',           str, 'Owner of the Sun Grid Engine job.'),
    ('name',            str, 'Job name.'), # sge 'job_name'
    ('id',              str, 'Job identifier.'), # sge 'job_number'
    ('account',         str, 'An account string as specified by the qsub(1) or qalter(1) -A option.'),
    ('priority',        int, 'Priority value assigned to the job corresponding to the priority parameter in the queue configuration (see queue_conf(5)).'),
    ('submission_time', int, 'Submission time (GMT unix time stamp).'),
    ('start_time',      int, 'Start time (GMT unix time stamp).'),
    ('end_time',        int, 'End time (GMT unix time stamp).'),
    ('failed',          int, 'Indicates the problem which occurred in case a job could not be started on the execution host (e.g. because the owner of the job did not have a valid account on that machine). If Sun Grid Engine tries to start a job multiple times, this may lead to multiple entries in the accounting file corresponding to the same job ID.'),
    ('exit_status',     int, 'Exit status of the job script (or Sun Grid Engine specific status in case of certain error conditions). The exit status is determined by following the normal shell conventions. If the command terminates normally the value of the command is its exit status. However, in the case that the command exits abnormally, a value of 0200 (octal), 128 (decimal) is added to the value of the command to make up the exit status. For example: If a job dies through signal 9 (SIGKILL) then the exit status becomes 128 + 9 = 137.'),
    ('ru_wallclock',    int, 'Difference between end_time and start_time.'),
    ('ru_utime',      float, ''), # Bogus.
    ('ru_stime',      float, ''), # Bogus.
    ('ru_maxrss',     float, ''), # Bogus.
    ('ru_ixrss',        int, ''), # Bogus.
    ('ru_ismrss',       int, ''), # Bogus.
    ('ru_idrss',        int, ''), # Bogus.
    ('ru_isrss',        int, ''), # Bogus.
    ('ru_minflt',       int, ''), # Bogus.
    ('ru_majflt',       int, ''), # Bogus.
    ('ru_nswap',      float, ''), # Bogus.
    ('ru_inblock',    float, ''), # Bogus.
    ('ru_oublock',      int, ''), # Bogus.
    ('ru_msgsnd',       int, ''), # Bogus.
    ('ru_msgrcv',       int, ''), # Bogus.
    ('ru_nsignals',     int, ''), # Bogus.
    ('ru_nvcsw',        int, ''), # Bogus.
    ('ru_nivcsw',       int, ''), # Bogus.
    ('project',         str, 'The project which was assigned to the job.'),
    ('department',      str, 'The department which was assigned to the job.'),
    ('granted_pe',      str, 'The parallel environment which was selected for that job.'), # '16way'
    ('slots',           int, 'The number of slots which were dispatched to the job by the scheduler.'),
    ('task_number',     int, 'Array job task index number.'),
    ('cpu',           float, 'The cpu time usage in seconds.'), # Bogus.
    ('mem',           float, 'The integral memory usage in Gbytes cpu seconds.'), # Bogus.
    ('io',            float, 'The amount of data transferred in input/output operations.'), # Bogus
    ('category',        str, 'A string specifying the job category.'),
    ('iow',           float, 'The io wait time in seconds.'), # Bogus.
    ('pe_taskid',       str, 'If this identifier is set the task was part of a parallel job and was passed to Sun Grid Engine via the qrsh -inherit interface.'),
    ('maxvmem',       float, 'The maximum vmem size in bytes.'), # Bogus.
    ('arid',            int, 'Advance reservation identifier. If the job used resources of an advance reservation then this field contains a positive integer identifier otherwise the value is 0.'),
    ('ar_submission_time', int, 'If the job used resources of an advance reservation then this field contains the submission time (GMT unix time stamp) of the advance reservation, otherwise the value is 0.'),
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
