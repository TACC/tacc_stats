import csv, os, subprocess, datetime, glob

def factory(batch_system,acct_path,host_name_ext):
  if batch_system == 'SGE':
    return SGEAcct(acct_path,host_name_ext)
  elif batch_system == 'SLURM':
    return SLURMAcct(acct_path,host_name_ext)

class BatchAcct(object):

  def __init__(self,batch_kind,acct_file,host_name_ext):
    self.batch_kind=batch_kind
    self.acct_file=acct_file
    self.field_names = [tup[0] for tup in self.fields]
    self.name_ext = '.'+host_name_ext

  def reader(self,start_time=0, end_time=9223372036854775807L, seek=0):
    """reader(start_time=0, end_time=9223372036854775807L, seek=0)
    Return an iterator for all jobs that finished between start_time and end_time.
    """
    file = open(self.acct_file)
    if seek:
      file.seek(seek, os.SEEK_SET)

    for d in csv.DictReader(file, delimiter=':', fieldnames=self.field_names):
      try:
        for n, t, x in self.fields:
          d[n] = t(d[n])
      except:
        pass
      ## Clean up when colons exist in job name
      d = self.clean_up(d)

      # Accounting records with pe_taskid != NONE are generated for
      # sub_tasks of a tightly integrated job and should be ignored.
      if max(start_time, d['end_time']) <= min(d['end_time'], end_time):
        if self.batch_kind=='SGE' and d['pe_taskid'] == 'NONE':
          yield d
        elif self.batch_kind=='SLURM':
          yield d

  def find_jobids(self, jobids):
    id_idx = self.field_names.index('id')
    sids = [str(jobid) for jobid in jobids]

    with open(self.acct_file) as fd:
      for line in fd:
        s = line.split(':')
        if s[id_idx] in sids:
          for d in csv.DictReader(line.splitlines(1),delimiter=':',fieldnames=self.field_names):
            try:
              for n, t, x in self.fields: d[n] = t(d[n])
            except: pass
            d = self.clean_up(d)
          yield d        
        

  def clean_up(self,d):
    if None not in d: return d
    num_cols = len(d[None])
    
    for cols in range(num_cols):
      d['name'] = d['name']+':'+d['status']        
      d['status'] = str(d['nodes'])
      d['nodes'] = d['cores']
      d['cores'] = d[None][0]
      del d[None][0]
    d['nodes'] = int(d['nodes'])
    d['cores'] = int(d['cores'])
    del d[None]
    return d

class SGEAcct(BatchAcct):

  def __init__(self, acct_file, host_name_ext):
    self.fields = (
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

    BatchAcct.__init__(self,'SGE',acct_file,host_name_ext)
    
  def keymap(key): # Batch account keywords are based on SGE names for
                   # historical reasons
    return key

  def get_host_list_path(self,acct,host_list_dir):
    """Return the path of the host list written during the prolog."""
    # Example: /share/sge6.2/default/tacc/hostfile_logs/2011/05/19/prolog_hostfile.1957000.IV32627
    start_date = datetime.date.fromtimestamp(acct['start_time'])
    base_glob = 'prolog_hostfile.' + acct['id'] + '.*'
    for days in (0, -1, 1):
      yyyy_mm_dd = (start_date + datetime.timedelta(days)).strftime("%Y/%m/%d")
      full_glob = os.path.join(host_list_dir, yyyy_mm_dd, base_glob)
      for path in glob.iglob(full_glob):
        return path
    return None




class SLURMAcct(BatchAcct):

  def __init__(self,acct_file,host_name_ext):
    
    self.fields = (
      ('id', str, 'Job ID'),
      ('uid', str, 'User UNIX ID'),
      ('project', str, 'SLURM account string'),
      ('yesno', str, 'Not sure yet, need to ask Karl'),
      ('start_time', int, 'Epoch time job started'),
      ('end_time', int, 'Epoch time job ended'),
      ('queue_time', int, 'Epoch time job entered queue'),
      ('queue', str, 'Name of the SLURM partition'),
      ('unknown', int, 'minutes requested?'),
      ('name', str, 'Name given to job by user'),
      ('status', str, 'SLURM job finish state: COMPLETED, FAILED, etc.'),
      ('nodes', int, 'Nodes requested'),
      ('cores', int, 'CPU cores requested')
      )
    
    BatchAcct.__init__(self,'SLURM',acct_file,host_name_ext)

  def get_host_list_path(self,acct,host_list_dir):
    """Return the path of the host list written during the prolog."""
    start_date = datetime.date.fromtimestamp(acct['start_time'])
    base_glob = 'hostlist.' + acct['id']
    for days in (0, -1, 1, -2, 2, -3, 3):
      yyyy_mm_dd = (start_date + datetime.timedelta(days)).strftime("%Y/%m/%d")
      full_glob = os.path.join(host_list_dir, yyyy_mm_dd, base_glob)

      for path in glob.iglob(full_glob):
        return path
    return None
