import csv

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
)

field_names = [tup[0] for tup in fields]

# Return an iterator for all jobs that finished between start_time and end_time.

def reader(file, start_time=0, end_time=9223372036854775807L):
    for d in csv.DictReader(file, delimiter=':', fieldnames=field_names):
        for n, t, x in fields:
            d[n] = t(d[n])
        if start_time <= d['end_time'] and d['end_time'] < end_time:
            yield d

# r_lis = [r for r in sge_acct.reader(open('accounting', 'r'))]
