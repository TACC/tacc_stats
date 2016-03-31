tacc_stats Documentation               {#mainpage}
========================

Developers and Maintainers
-------
R. Todd Evans  (<mailto:rtevans@tacc.utexas.edu>)
Bill Barth     (<mailto:bbarth@tacc.utexas.edu>)

Original Developer
-------
John Hammond


Description
-----------------
The tacc_stats package provides the tools to monitor resource usage of HPC systems at multiple levels of resolution.

The package is split into an `autotools`-based `monitor` subpackage and a Python `setuptools`-based `tacc_stats` subpackage.  `monitor` performs the online data collection and transmission in a production environment while `tacc_stats` performs the data curation and analysis in an offline environment.

Installing `monitor` will build and install an System V service, `/etc/init.d/taccstats`.  This service launches a daemon with an overhead of 3-9% on a single core when configured to sample at a frequency of 1Hz.  It is typically configured to sample at 10 minute intervals, with samples taken at the start and end of every job as well. `tacc_stats` sends the data directly to a RabbitMQ server over the administrative ethernet network.  RabbitMQ must be installed and running on the server in order for the data to be received.

Installing the `tacc_stats` module will setup a Django-based web application along with tools for extracting the data from the RabbitMQ server and feeding them into a PostgreSQL database.   

Code Access
-----------
To get access to the tacc_stats source code clone this repository:

    git clone https://github.com/TACC/tacc_stats


----------------------------------------------------------------------------

Installation
--------
#### `monitor` subpackage

First ensure the RabbitMQ library and header file are installed on the build and compute nodes

[librabbitmq-devel-0.5.2-1.el6.x86_64](ftp://fr2.rpmfind.net/linux/epel/6/x86_64/librabbitmq-devel-0.5.2-1.el6.x86_64.rpm)

`./configure --enable-rabbitmq; make; make install` will then successfully build the `tacc_stats` executable for many systems.  If Xeon Phi coprocessors are present on your system they can be monitored with the `--enable-mic` flag.  Additionally the configuration options, `--disable-infiniband`, `--disable-lustre`, `--disable-hardware` will disable infiniband, Lustre Filesystem, and Hardware Counter monitoring.  Not enabling RabbitMQ will result in a legacy build of `tacc_stats` that relies on the shared filesystem to transmit data.  This mode is not recommended.  If libraries or header files are not found than add their paths to the include and library paths with the `CPPFLAGS` and/or `LDFLAGS` vars as usual.  

There will be a configuration file, `/etc/tacc_stats.conf`, after installation.  This file contains the fields

`SERVER=localhost`

`QUEUE=default`

`PORT=5672`

`FREQ=600`


`SERVER` should be set to the RabbitMQ server, `QUEUE` to the system name, `PORT` to the RabbitMQ port (5672 should be ok), and `FREQ` to the desired sampling frequency in seconds.

An RPM can be built for subpackage deployment using  the `tacc_statsd.spec` file.  The most straightforward approach to build this
is to setup your rpmbuild directory then

`rpmbuild -ba tacc_statsd.spec --define 'rmqserver rabbitmqservername' --define 'system systemname'`

where the `rmqserver` will be the RabbitMQ `SERVER` hostname and `system` will be the `QUEUE` in `tacc_stats.conf`. 

After installation the executable `/opt/tacc_statsd/tacc_stats`, service `/etc/init.d/taccstats`, and config file `/etc/tacc_stats.conf` should exist.  If the rpm was used for installation `tacc_stats` will be `chkconfig`'d to start at boot time and be running.
`tacc_stats` can be started, stopped, and restarted using `taccstats start`, `taccstats stop`, and `taccstats restart`.

In order to notify `tacc_stats` of a job beginning echo the job id into `/var/run/TACC_jobid`.  It order to notify
it of a job ending echo `-` into `/var/run/TACC_jobid`.  This can be accomplished in the job scheduler prolog and
epilog for example.

   
#### `tacc_stats` subpackage
 To install TACC Stats on the machine where data will be processed, analyzed, and the webserver hosted follow these
 steps:
 
1. Download the package and setup the Python virtual environment.

```
$ virtualenv machinename --system-site-packages
$ cd machinename; source bin/activate
$ git clone https://github.com/TACC/tacc_stats
```

`tacc_stats` is a pure Python package.  Dependencies should be automatically downloaded
and installed when installed via `pip`.  The package must first be configured however.  


2. The initialization file, `tacc_stats.ini`, controls all the configuration options and has 
the following content and descriptions

```
## Basic configuration options - modify these
# machine       = unique name of machine/queue
# server        = database and rmq server hostname
# data_dir      = where data is stored
[DEFAULT]
machine         = ls5
data_dir        = /hpc/tacc_stats_site/%(machine)s
server          = tacc-stats02.tacc.utexas.edu

## RabbitMQ Configuration
# RMQ_SERVER    = RMQ server
# RMQ_QUEUE     = RMQ server
[RMQ]
rmq_server      = %(server)s
rmq_queue       = %(machine)s

## Configuration for Web Portal Support
[PORTAL]
acct_path       = %(data_dir)s/accounting/tacc_jobs_completed
host_list_dir   = %(data_dir)s/hostfile_logs
pickles_dir     = %(data_dir)s/pickles
archive_dir     = %(data_dir)s/archive
host_name_ext   = %(machine)s.tacc.utexas.edu
batch_system    = SLURM
```

Set these paths as needed.  The raw stats data will be stored in the `archive_dir` and processed stats data in the `pickles_dir`.  `machine` should match the system name used in the RabbitMQ server `QUEUE` field.  This is the only field that needs to match 
anything in the `monitor` subpackage.

3. Install `tacc_stats`
```
$ pip install tacc_stats/
```

4. Start the RabbitMQ server reader in the background, e.g. 
```
$ nohup listend.py > /tmp/listend.log
```
Raw stats files will now be generated in the `archive_dir`.

5. A PostgreSQL database must be setup on the host.  To do this, after installation
run
```
$ python manage.py migrate
```
This will generate a table named `machine_db` in your database.  

6. Setup cron jobs to process raw data and ingest into database.  Add the following to your 
cron file
```
*/15 * * * * source /home/rtevans/testing/bin/activate; job_pickles.py; update_db.py > /tmp/ls5_update.log 2>&1
```

7. Next configure the Apache server (make sure it is installed and the `mod_wsgi` Apache module is installed)
A sample configuration file, `/etc/httpd/conf.d/ls5.conf`, looks like
```
LoadModule wsgi_module modules/mod_wsgi.so
WSGISocketPrefix run/wsgi
<VirtualHost *:80>
ServerAdmin rtevans@tacc.utexas.edu
ServerName tacc-stats02.tacc.utexas.edu
ServerAlias ls5-stats.tacc.utexas.edu
WSGIDaemonProcess ls5 python-path=/usr/lib/python2.7/site-packages:/home/rtevans/tacc_stats
WSGIProcessGroup ls5
WSGIScriptAlias / /home/rtevans/tacc_stats/tacc_stats/site/tacc_stats_site/wsgi.py
WSGIApplicationGroup %{GLOBAL}
<Directory /home/rtevans/tacc_stats/tacc_stats/site/tacc_stats_site>
<Files wsgi.py>
Require all granted
</Files>
</Directory>
</VirtualHost>
```

8. Start up Apache 

Job Scheduler Configuration
-------
In order for tacc_stats to correcly label records with JOBIDs it is required that
the job scheduler prolog and epilog contain the lines


`echo $JOBID > jobid_file`  

`echo - > jobid_file`

To perform the pickling of this data it is also necessary to
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

\warning Stats from a given job on a give host may span multiple files.


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

## Miscellaneous Information

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

    
    For the source and meanings of the counters, see the tacc_stats source
    `https://github.com/rtevans/tacc_stats`, the CentOS 5.6 kernel source,
    especially `Documentation/*`, and the manpages, especially proc(5).


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
