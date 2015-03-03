tacc_stats Documentation               {#mainpage}
========================

Authors
-------
Bill Barth     (<mailto:bbarth@tacc.utexas.edu>)    
R. Todd Evans  (<mailto:rtevans@tacc.utexas.edu>)  


Executive Summary
-----------------
The tacc_stats repository consists of four complementary modules:

1. `monitor` is a job-oriented and logically structured version of the conventional sysstat system monitor. 

2. `pickler` is a Python module that collects the node-based raw stats 
data into job-based pickled Python dictionaries.

3. `analysis` is a Python module that runs over a job list performing tests, computing metrics, and 
generating plots. 

4. `site` is a Python module based on Django that builds a database and 
website that allows exploration and visualization of data at the job, user, project, application, and/or system level.
It interfaces with a Postgres Database and optionally an XALT Database (https://github.com/Fahey-McLay).

Code Access
-----------
To get access to the tacc_stats source code 

    git clone https://github.com/TACC/tacc_stats


----------------------------------------------------------------------------

Building
--------
### Quickstart
These commands quickly build and install the TACC Stats package into your
'~/.local/' directory.  You should customize the tacc_stats/setup.cfg file
for your site specific paths and devices.  The modality of TACC Stats is 
chosen under the OPTIONS section of the setup.cfg file.  There are 
currently three modes available:

1. RabbitMQ sends data off node to central location at collection time (RMQ = True) & TACC Stats is run as a linux-style init.d daemon service (MODE = DAEMON).

2. RabbitMQ sends data off node to central location at collection time (RMQ = True) & TACC Stats is run as a cron job (MODE = CRON).

3. Data is stored on local node and archived daily via rsync to central location (RMQ = FALSE) & TACC Stats is run as a cron job (MODE = CRON).
   
To install TACC Stats on the machine where data will be analyzed do the following:
~~~
    $ git clone https://github.com/TACC/tacc_stats
    $ pip install --user -e tacc_stats
~~~

Scripts and executables will be installed in 
'~/.local/bin' and Python modules in '~/.local/lib'.  In order for RMQ mode to recieve data the rabbitmq-server must
be started and the `amqp_listend` executable started. `amqp_listend -s SERVERNAME -a ARCHIVEDIR` will start a daemon that consumes tacc_stats data from the server running RabbitMQ `SERVERNAME` and outputs the data as textfiles to the `ARCHIVEDIR`.

To install TACC Stats on the compute nodes the recommended approach is to generate an rpm:
~~~
    $ git clone https://github.com/TACC/tacc_stats
    $ cd tacc_stats
    $ python setup.py bdist_rpm
~~~
This will generate an rpm in the newly created dist/ directory. 
To configure the build for a particular site, create a new file in the `cfg/` directory similar to the other $system.cfg files already in there, with paths configured for your system's setup.  Place the name of that file in the top-level directory file `setup.cfg` on the `SITE_CFG` line.  Paths must be set and Types of devices to collect will be labeled True to activate or False to deactivate.  The chip device collectors will test whether it monitor is running on the correct architecture for the given collector.  This allows multiple chip architectures to be collected using the same build.
Note `hsw`, `snb`, `wtm`, `nhm`, `amd` are for Haswell, Sandybridge/Ivy Bridge, Westmere, Nehalem, and AMD architectures.
The corresponding hyper-threaded versions will be suffixed with a `_ht` if available.

This will generate an rpm that will install the executable `tacc_stats_monitord` in the directory specified by the `exe_path` field in `setup.cfg`.  When compiled in 
cron mode without RabbitMQ the installation of the rpm will setup a cron task that rsyncs data daily to the `tacc_stats_home` directory.  When compiled in RabbitMQ mode the rpm will setup a cron task that sends data to the `SERVER` specified in `setup.cfg`.  When compiled in RabbitMQ and DAEMON mode the installation will install the service `taccstats` which can
be run as a linux-style `/etc/init.d` service.  The installation is also compatible with `systemd` type operating systems.


### Detailed Install

1. *Introduction*
The build system uses Python's `distutils` module.  The C extensions 
and Python modules for a particular site are configured using the `setup.cfg`.  
Thus the configure file `setup.cfg` should be customized for your site before installation.
The installation will place a number of scripts into the Python `bin`
directory and the modules in the Python `lib` directory.

2. *Configure*
All configuration is specified in the `setup.cfg` file. 

The meaning of every field in the `[OPTIONS]` section are as follows:

    `RMQ`               True/False Whether to use RabbitMQ messaging for sending data or rely on rsync
    
    `MODE`              DAEMON/CRON Whether to build `monitord` as a cron launched application or daemon service
    
    `SERVER`            The server which accepts data from all nodes
    
    `FREQUENCY`         The frequency at which samples are taken in DAEMON mode

The meaning of every field  in the `[PATH]` section is specified here:

    `exe_path`           Location to install `monitord` and `amqp_listend`

    `stats_dir`          The directory that `monitor` writes to

    `stats_lock`         The file that `monitor` uses to lock during counter reads

    `jobid_file`         The file that contains the Job ID of the currently monitored job

    `tacc_stats_home`    The directory in which `archive` (all node-based data) will be contained

    `acct_path`          The accounting file generated by the job scheduler

    `host_list_dir`      The directory than contains each job's host list

    `batch_system`       SLURM or SGE are currently supported

    `host_name_ext`      The extension of the hostnames, e.g. stampede.tacc.utexas.edu

    `pickles_dir`        The directory the pickles files will be stored to and read from.

    `lariat_path`        The directory the lariat data (if any) is read from.

    The `[TYPES]` section lists the devices that are currently readable.
    They are set to True or False depending on whether they are on the
    system.  If the computing platform is missing any `TYPES` that are left as True that type 
    will automatically be skipped during the monitoring.

3. *Build*
There are currently three approaches to building and installing the package.

    1) `pip`,`easy_install`, or `python setup.py install`: install all perform the same build and 
    install steps.  The package entire is installed using this approach.

    2) `python setup.py bdist_rpm`: this builds an rpm in the `tacc_stats/dist`
    directory.  The rpm will install the entire package and place a setuid'd root
    version of monitor called `tacc_stats` in `/opt/tacc_stats`.  It will also modify
    crontab to run `tacc_stats` every 10 minutes (configurable) and run `archive.sh`
    every night at a random time between 2am and 4am.  `archive.sh` copies the data
    in `stats_dir` to `tacc_stats_home`.  It is used at TACC to move data from local
    storage on the compute nodes to a central filesystem location.

    3) `python setup.py bdist_rpm`: this builds an rpm in the `tacc_stats/dist`
    directory.  The rpm will install only the `monitor` package and place a setuid'd root
    version of monitor called `tacc_stats_monitord` in `/opt/tacc_stats`.  It will also modify
    crontab to run `tacc_stats` every 10 minutes (configurable) and run `archive.sh`
    every night at a random time between 2am and 5am. This is the preferred method
    for installations to the compute nodes.  In the DAEMON mode tacc_stats will be installed
    as the /etc/init.d service taccstats.

    The first two installation methods are most suited to analysis nodes.  They are
    reasonable heavyweight and require several Python packages.  The third approach is
    extremely light-weight and requires only a Python installation.  Both rpm based
    methods set `tacc_stats` and `archive.sh` running automatically.

----------------------------------------------------------------------------

Running
-------
Installation method 3 should be used to setup monitoring of compute nodes.  In order for 
tacc_stats to correcly label records with JOBIDs it is required that
the job scheduler prolog and epilog contain the lines 
in CRON mode 

`echo $JOBID > jobid_file`  
`tacc_stats begin $JOBID`

and 

`tacc_stats end $JOBID`
`echo 0 > jobid_file`

or in DAEMON mode

`service taccstats begin $JOBID`
and
`service taccstats end $JOBID`

respectively.  To perform the pickling of this data it is also necessary to 
generate an accounting file that contains at least the JOBID and time range 
that the job ran.  The pickling will currently work without modification on 
SGE job schedulers.  It will also work on any accounting file with the format

`$JOBID : UID : Project ID : Junk : Start time : End time : Time place in queue : SLURM partition : Junk : Job name : Job completion status : Nodes : Cores`

for each record using the SLURM interface.  In addition to the accounting file,
a directory of host-file logs (hosts belonging to a particular job) must be
generated.  The accounting file and host-file logs are used to map JOBID's to 
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

The `TYPES` that can be collected are:

  ~~~
  amd64_pmc         AMD Opteron performance counters (per core)
  intel_nhm         Intel Nehalem Processor          (per core)
  intel_uncore      Westmere Uncore                  (per socket)
  intel_snb         Intel Sandy Brige Processor      (per core)
  intel_snb_cbo     Caching Agent (CBo)              (per socket)
  intel_snb_pcu     Power Control Unit               (per socket)
  intel_snb_imc     Integrated Memory Controller     (per socket)
  intel_snb_qpi     QPI Link Layer                   (per socket)
  intel_snb_hau     Home Agent Unit                  (per socket)
  intel_snb_r2pci   Ring to PCIe Agent               (per socket)
  ib                Infiniband usage                 
  ib_sw             InfiniBand usage
  ib_ext            Infiniband usage
  llite             Lustre filesystem usage (per mount),
  lnet              Lustre network usage
  mdc               Lustre network usage
  osc               Lustre filesystem usage
  block             block device statistics (per device),
  cpu               scheduler accounting (per CPU),
  mem               memory usage (per socket)
  net               network device usage (per device)
  nfs               NFS system usage
  numa              weird NUMA statistics (per socket),
  ps                process statistics,
  sysv_shm          SysV shared memory segment usage,
  tmpfs             ram-backed filesystem usage (per mount),
  vfs               dentry/file/inode cache usage,
  vm                virtual memory statistics.
  ~~~

The `TYPES` to include in a build of tacc_stats are specified in 
the `setup.cfg` list `TYPES`.  To add a new `TYPE` to tacc_stats,
write the appropriate `TYPENAME.c` file and place it in the `src/monitor/` directory.
Then add the `TYPENAME` to the `TYPES` list.
 
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

