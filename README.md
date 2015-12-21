tacc_stats Documentation               {#mainpage}
========================

Authors
-------
R. Todd Evans  (<mailto:rtevans@tacc.utexas.edu>)
Bill Barth     (<mailto:bbarth@tacc.utexas.edu>)



Description
-----------------
The tacc_stats package provides the tools to monitor resource usage of HPC systems at multiple levels of resolution.

The package is organized into four heirarchical modules.  The core of the package is the `monitor` module.  This module collects data from the compute nodes.  It produces raw text files that may then be processed by the `pickler` module.
The `pickler` module processes the raw node-level text files into a single binary Python pickle file for each job.  The pickle files may then be tested and plotted by the `analysis` module.  Finally, the `site` module ingests data from the pickle files and `analysis` module's tests into a database that may be queried using a web interface.  Additional details for each module follow:

1. `monitor` is an automatic node-level system monitor that collects resource usage data from hardware performance counters and the /sys and /proc filesystems.  It currently can be configured  to operate in two distinct modes.  The first mode is driven by `cron` and relies on copies over the shared file-system to aggregate data.  The second mode operates as a daemon and is controlled by the `/etc/init.d/taccstats` script.  Both versions require a signal at the start and end of each job.  This is accomplished at TACC using the prolog and epilog scripts that are run by the job scheduler at the start and end of each job.

2. `pickler` is a Python module that processes the node-level data into job-level pickled Python dictionaries.  It attempts to clean the data by handling counter overflow and standarding units of measurement.  It also translates chip event codes (in hex) to human readable event names.  

3. `analysis` is a Python module that performs tests, computes metrics, and can generate plots for jobs or groups of jobs.

4. `site` is a Python module built on Django that builds a database and
website that allows exploration and visualization of data at the job, user, project, application, and/or system level.
It interfaces with a Postgres Database and optionally an XALT Database (https://github.com/Fahey-McLay).  Tests are automatically applied daily to all jobs.  These tests attempt to identify jobs that were distressed or performing in a sub-optimal manner.  Plots are also generated on the fly to represent data at several levels.  

Code Access
-----------
To get access to the tacc_stats source code clone this repository:

    git clone https://github.com/TACC/tacc_stats


----------------------------------------------------------------------------

Building tacc_stats
--------

#### `monitor` module
The monitor module is built and installed as an rpm generated by the Python `distutils` package. The rpm installs a C executable that
runs at regular intervals on each compute node.  A few modification to the job scheduler will also be necessary.  Steps for building the executable and modifying the job scheduler follow:


1. Clone the repository enter the top-level directory and open the `setup.cfg` file.  This file is used to configure the module.  There are two modes available to build and run the module.   They are specified in `setup.cfg` as follows

  * **CRON**   set MODE and RMQ fields to  `MODE = CRON` and `RMQ =  False`

    The CRON mode rpm will install an executable (`/opt/tacc_stats/tacc_stats`) and install a crontab file (`/etc/crond.d/tacc_stats`) that runs the executable every ten minutes.  The data is saved locally to the node.  Every 24 hours the data is copied over the shared file-system to a central location using the script `/opt/tacc_stats/archive.sh` which is also installed by the rpm.
  * **DAEMON** set the MODE and RMQ fields to `MODE = DAEMON` and `RMQ = True`

    The DAEMON mode rpm will install an executable (`/opt/tacc_statsd/tacc_statsd`) and install a control script (`/etc/init.d/taccstats`).  This mode is dependent on the libraries

    [librabbitmq-devel-0.5.2-1.el6.x86_64](ftp://fr2.rpmfind.net/linux/epel/6/x86_64/librabbitmq-devel-0.5.2-1.el6.x86_64.rpm)

    [librabbitmq-0.5.2-1.el6.x86_64](ftp://fr2.rpmfind.net/linux/epel/6/x86_64/librabbitmq-0.5.2-1.el6.x86_64.rpm)

    These libraries should be installed in the locations specified under the build_ext section.  If they end up in a different location then change those fields accordingly.  The frequency in seconds of sample collection for the DAEMON mode is set by `FREQUENCY = 600`.  The daemon sends the data immediately to the RabbitMQ server running on the host specified by the `SERVER` field.

  Someday the capability to mix and match modes will be available but we aren't there yet.  Finally, set the `SITE_CFG` field to a file in the `cfg/` directory.

2.  The file you create in the `cfg` directory will set site specific paths to libraries, hints about architecture, and paths to store data, and the server that will accept the data and host the database and website. The sections of the config file are described below

###`[DEFAULT]`
    `machine`               unique name of machine to monitor
    `base_dir`              directory data is stored in
    `server`                database and rmq server hostname
###`[OPTIONS]`    
    `MODE`                  DAEMON/CRON
    `FREQUENCY`             Sampling Frequency
    `IB`                    True/False sample Infiniband devices
    `LFS`                   True/False sample Lustre FS devices
    `Phi`                   True/False sample Xeon Phi Coprocessor
###`[RMQ_CFG]` # RabbitMQ Configuration
    `rmq_path`              path to rabbitmq inc and lib dirs
    `RMQ_SERVER`            %(server)s #RMQ server fqdn name
    `HOST_NAME_QUEUE`       %(machine)s # Queue to use in rabbitmq

###`[MONITOR_PATHS]`## Paths for monitor program (defaults work)
    `stats_dir`             local data storage directory
    `stats_lock`            lock file
    `jobid_file`            job id file
    `archive_dir`           %(base_dir)s/archive
###`[PORTAL_OPTIONS]` # Configuration for Web Portal Support
    `acct_path`             %(base_dir)s/accounting/tacc_jobs_completed
    `host_list_dir`         %(base_dir)s/hostfile_logs
    `pickles_dir`           /corral-repl/tacc/hpc/tacc_stats_site/stampede/pickles
    `host_name_ext`         %(machine)s.tacc.utexas.edu
    `tacc_stats_home`       %(base_dir)s
    `batch_system`          SLURM or SGE

There is a large variety of data collected and summarized below:    

      `amd64_pmc`         AMD Opteron performance counters (per core)

      `intel_hsw`         Intel Haswell Processor (HSW)         (per core)

      `intel_hsw_ht`      Intel Haswell Processor - Hyper-threaded (per logical core)

      `intel_nhm`         Intel Nehalem Processor (NHM)         (per core)

      `intel_uncore`      Westmere Uncore          (WTM)        (per socket)

      `intel_snb`         Intel Sandy Brige (SNB) or Ivy Bridge (IVB) Processor      (per core)

      `intel_snb(hsw)_cbo`     Caching Agent (CBo) for SNB (HSW)              (per socket)

      `intel_snb(hsw)_pcu`     Power Control Unit for SNB (HSW)               (per socket)

      `intel_snb(hsw)_imc`     Integrated Memory Controller for SNB (HSW)     (per socket)

      `intel_snb(hsw)_qpi`     QPI Link Layer for SNB (HSW)                  (per socket)

      `intel_snb(hsw)_hau`     Home Agent Unit for SNB (HSW)                 (per socket)

      `intel_snb(hsw)_r2pci`   Ring to PCIe Agent for SNB (HSW)               (per socket)

      `ib`                Infiniband usage

      `ib_sw`             InfiniBand usage

      `ib_ext`            Infiniband usage

      `llite`             Lustre filesystem usage (per mount),

      `lnet`              Lustre network usage

      `mdc`               Lustre network usage

      `mic`              MIC scheduler account (per hardware thread)

      `osc`               Lustre filesystem usage

      `block`             block device statistics (per device)

      `cpu`               scheduler accounting (per CPU)

      `mem`               memory usage (per socket)

      `net`               network device usage (per device)

      `nfs`               NFS system usage

      `numa`              weird NUMA statistics (per socket)

      `proc`              Process specific data (MaxRSS, executable name etc.)

      `ps`                process statistics

      `sysv_shm`          SysV shared memory segment usage

      `tmpfs`             ram-backed filesystem usage (per mount)

      `vfs`               dentry/file/inode cache usage

      `vm`                virtual memory statistics.

    The `TYPES` to include in a build of tacc_stats are specified in
    the `setup.cfg` list `TYPES`.  To add a new `TYPE` to tacc_stats,
    write the appropriate `TYPENAME.c` file and place it in the `src/monitor/` directory.
    Then add the `TYPENAME` to the `TYPES` list and set that `TYPE` to equal True.  To disable a `TYPE` set it equal to False.

    For the keys associated with each `TYPE`, see the appropriate schema.
    For the source and meanings of the counters, see the tacc_stats source
    `https://github.com/rtevans/tacc_stats`, the CentOS 5.6 kernel source,
    especially `Documentation/*`, and the manpages, especially proc(5).

    I have not tracked down the meanings of all counters.  However, if I
    did (and it wasn't obvious from the counter name) then I put that
    information in the source (see for example `block.c`).

    All intel Sandy Bridge core and uncore counters are documented in detail
    in their corresponding source code and via Doxygen, e.g. `intel_snb.c`.
    Many processor-related performance counters are configurable using their
    corresponding control registers.  The use of these registers is described
    in the source code and Doxygen.  

3. After the `.cfg` files have been created and/or set run

    `python setup.py bdist_rpm`

An rpm will be generated and placed in the newly created `dist/` directory. Upon installation of the rpm tacc_stats should be running automatically.

#### `pickler`, `analysis`, `site` modules

To install TACC Stats on the machine where data will be processed, analyzed, and the webserver hosted run the following commands on the server it will be hosted from:
~~~
    $ virtualenv machinename
    $ cd machinename; source bin/activate
    $ git clone https://github.com/TACC/tacc_stats
    $ pip install -e tacc_stats/
~~~

Scripts and executables will be installed in
'machinename/bin' and Python modules in 'machinename/lib'.  
Ensure that the accounting file, hostfiles, and node-level stats data are
visible to the server.

##### RabbitMQ Enabled Version
In order for RMQ mode to receive data the rabbitmq-server must be started and the `amqp_listend` daemon started :

`amqp_listend -s SERVERNAME -a ARCHIVEDIR`

will start a daemon that consumes tacc_stats data from the server running RabbitMQ `SERVERNAME` and outputs the data as textfiles to the `ARCHIVEDIR`.  Be careful that the `host_name_ext` specified in your site specific configuration file is the same as what was set on the compute nodes.  `amqp_listend` uses this parameter
to locate the correct data (the RabbitMQ queue is named by this parameter).




Job Scheduler Configuration
-------
In order for tacc_stats to correcly label records with JOBIDs it is required that
the job scheduler prolog and epilog contain the lines
in CRON mode

`echo $JOBID > jobid_file`  
`tacc_stats begin $JOBID`

and

`tacc_stats end $JOBID`    
`echo 0 > jobid_file`

and in DAEMON mode

`service taccstats start`    
`service taccstats begin $JOBID`  

and

`service taccstats end`  

respectively.  To perform the pickling of this data it is also necessary to
generate an accounting file that contains at least the JOBID and time range
that the job ran.  The pickling will currently work without modification on
SGE job schedulers.  It will also work on any accounting file with the format

`Job ID ($JOBID) : User ID ($UID) : Project ID ($ACCOUNT) : Junk ($BATCH) : Start time ($START) : End time ($END) : Time job entered in queue ($SUBMIT) : SLURM partition ($PARTITION) : Requested Time ($LIMIT) : Job name ($JOBNAME) : Job completion status ($JOBSTATE) : Nodes ($NODECNT) : Cores ($PROCS)`

for each record using the SLURM interface (set by the `batch_system` field in the site-specific configuration file).  In addition to the accounting file, a directory of host-file logs (hosts belonging to a particular job) must be
generated. The host file directories should have the form

`/year/month/day/hostlist.JOBID`

with hostlist.JOBID listing the hosts allocated to the job in a single column.

The accounting file and host-file logs will be used to map JOBID's to
time and node ranges so that the job-level data can be extracted from the
raw data efficiently.

As mentioned above the `monitor` module produces a light-weight C
code called `monitor` which is setuid'd to `/opt/tacc_stats/tacc_stats_monitord`.  It is called at the beginning of every job to configure Performance Monitoring Counter registers
for specific events.  As the job is running `tacc_stats_monitord` is called at regular intervals (the default is 10 mn) to collect the counter registers values at regular time
intervals.  This counter data is stored in "raw stats" files.  These
stats files are node-level data labeled by JOBID and may or may not be
locally stored, but must be visible to the node as a mount.

### Running `tacc_stats`

`tacc_stats` can be run manually in CRON mode by:

    $ tacc_stats begin jobid
    $ tacc_stats collect

However, it is typically invoked by setting up cron scripts and prolog/epilog files as
described in the example below, which corresponds to its usage on Stampede.

#### Example

- Invocation:
    - CRON
`tacc_stats_monitord` runs every 10-minutes (through
cron), and at the beginning and end of every job (through SLURM
prolog/epilog).  In addition, `tacc_stats` may be directly invoked by
the user (or application) although we have not advertised this.
    - DAEMON
`tacc_stats_monitord` runs every 10-minutes, or the frequency in seconds specified in `setup.cfg` under the `FREQUENCY` field (as a DAEMON), and at the beginning and end of every job (through SLURM
prolog/epilog).
- Data Handling:
On each invocation, `tacc_stats_monitord` collects and records system statistics
to a structured text file on ram backed storage local to the node or else sends the
data to a central server location where it is immediately written to textfiles by
the `amqp_listend` daemon.
Stats files are typically rotated at every night.  
In CRON mode
A stats file created at epoch time `EPOCH`, on
node `HOSTNAME`, will be stored locally as `/var/log/tacc_stats/EPOCH`,
and archived at
`/scratch/projects/tacc_stats/archive/HOSTNAME/EPOCH.gz`.
In DAEMON mode the data will be immediately sent to a server and
available for analysis.

\warning Do not expect all stats files to be created at midnight
exactly, or even approximately.  As nodes are rebooted, new
stats_files will be created as soon as a job begins or the cron task
runs.

\warning Stats from a given job on a give host may span multiple files.

\warning Expect stats files to be missing occasionally, as nodes may
crash before they can be archived.  Since we use ram backed storage
these files do not survive a reboot.

### Running `job_pickles.py`
`job_pickles.py` can be run manually by:

    $ ./job_pickles.py [-start date_start] [-end date_end] [-dir directory] [-jobids id0 id1 ... idn]

where the 4 optional arguments have the following meaning

  - `-dir`       : the directory to store pickled dictionaries
  - `-start`     : the start of the date range, e.g. `"2013-09-25 00:00:00"`
  - `-end`       : the end of the date range, e.g. `"2013-09-26   00:00:00"`
  - `jobids`     : individual jobids to pickle
  -
No arguments results in all jobs from the previous day getting pickled and stored in the `pickles_dir`
defined in `setup.cfg`. On Stampede argumentless `job_pickles.py` is run every 24 hours as a `cron` job
set-up by the user

For pickling data with Intel Sandy Bridge core and uncore counters it is useful to
modify the event_map dictionaries in `intel_snb.py` to include whatever events you are counting.The dictionaries map a control register value to a Schema name.  
You can have events in the event_map dictionaries that you are not counting,
but if missing an event it will be labeled in the Schema with it's control register
value.

----------------------------------------------------------------------------

Stats Data
----------

### Raw stats data: generated by `tacc_stats`

A raw stats file consists of a multiline header, followed my one or more
record groups.  The first few lines of the header identify the version
of tacc_stats, the FQDN of the host, it's uname, it's uptime in seconds, and
other properties to be specified.

    $tacc_stats 1.0.2
    $hostname i101-101.ranger.tacc.utexas.edu
    $uname Linux x86_64 2.6.18-194.32.1.el5_TACC #18 SMP Mon Mar 14 22:24:19 CDT 2011
    $uptime 4753669

These are followed by schema descriptors for each of the types collected:

    !amd64_pmc CTL0,C CTL1,C CTL2,C CTL3,C CTR0,E,W=48 CTR1,E,W=48 CTR2,E,W=48 CTR3,E,W=48
    !cpu user,E,U=cs nice,E,U=cs system,E,U=cs idle,E,U=cs iowait,E,U=cs irq,E,U=cs softirq,E,U=cs
    !lnet tx_msgs,E rx_msgs,E rx_msgs_dropped,E tx_bytes,E,U=B rx_bytes,E,U=B rx_bytes_dropped,E
    !ps ctxt,E processes,E load_1 load_5 load_15 nr_running nr_threads
    ...

A schema descriptor consists of the character '!' followed by the
type, followed by a space separated list of elements.  Each element
consists of a key name, followed by a comma-separated list of options;
the options currently used are:
  - E meaning that the counter is an event counter,
  - W=<BITS> meaning that the counter is <BITS> wide (as opposed to 64),
  - C meaning that the value is a control register, not a counter,
  - U=<STR> meaning that the value is in units specified by <STR>.

Note especially the event and width options.  Certain counters, such
as the performance counters are subject to rollover, and as such their
widths must be known for the values to be interpreted correctly.

\warning The archived stats files do not account for rollover.  This
task is left for postprocessing.

A record group consists of a blank line, a line containing the epoch
time of the record and the current jobid, zero of more lines of marks
(each starting with the % character), and several lines of statistics.

    1307509201 1981063
    %begin 1981063
    amd64_pmc 11 4259958 4391234 4423427 4405240 235835341001110 187269740525248 62227761639015 177902917871843
    amd64_pmc 10 4259958 4391234 4405239 4423427 221601328309784 187292967300939 47879507215852 174113618669738
    amd64_pmc 13 4259958 4405238 4391234 4423427 211997466129346 215850892876689 2218837366391 233806061617899
    amd64_pmc 12 4392928 4259958 4391234 4423427 6782043270201 102683296940807 2584394368284 174209034378272
    ...
    cpu 11 429720418 0 1685980 43516346 447875 155 3443
    cpu 10 429988676 0 1675476 43150935 559410 8 283
    ...
    net ib0 0 0 55915434547 0 0 0 0 0 0 0 0 0 159301288 0 46963995550 0 0 97 0 0 0 31404022 0
    ...
    ps - 4059349377 507410 1600 1600 1600 18 373
    ...

Each line of statistics contains the type (amd64_pmc, cpu, net,
ps,...), the device (11,10,13,12,...,ib0,-...), followed by the
counter values in the order given by the schema.  Note that when we
cannot meaningfully attach statistics to a device, we use '-' as the
device name.


### `TYPES`


\note All chip architecture related types are checked for existence at
run time.  Therefore, it is unnecessary for the user to filter for
these types listed above - they will be filtered at run time.  This
should also work well for systems composed of multiple types of chip
architectures.

\warning Due to a bug in Lustre, llite overreports read_bytes.

\warning Some event counters (from ib_sw, numa, and possibly others)
suffer from occasional dips.  This may be due to non-atomic accesses
in the (kernel) code that presents the counter, a bug in tacc_stats,
or some other condition.  Spurious rollover is easy to detect,
however, because a naive adjustment produced a riduculously large
delta.

\warning We never reset counters, thus to determine the number of
events that occurred during a job, you must subtract the value at
begin from end.

\warning Due to a quirk in the Opteron performance counter
architecture, we do not assign the same set of events to each core,
see `amd64_pmc.c` in the tacc_stats source for details.

### Pickled stats data: generated `job_pickles.sh`

Pickled stats data will be placed in the directory specified by
`pickles_dir`.  The pickled data is contained in a nested python
dictionary with the following key layers:

    job       : 1st key Job ID
     host     : 2nd key Host node used by Job ID
      type    : 3rd key TYPE specified in tacc_stats
       device : 4th key device belonging to type

For example, to access Job ID `101`'s stats data on host `c560-901` for
`TYPE` `intel_snb` for device cpu number `0` from within a python script:

    pickle_file = open('101','r')
    jobid = pickle.load(pickle_file)
    pickle_file.close()
    jobid['c560-901']['intel_snb']['0']

The value accessed by this key is a 2D array, with rows corresponding to record times and
columns to specific counters for the device.  To view the names for each counter add

    jobid.get_schema('intel_snb')

or for a short version

    jobid.get_schema('intel_snb').desc

----------------------------------------------------------------------------

## Copyright
(C) 2011 University of Texas at Austin

## License

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
