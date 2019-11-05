tacc_stats Documentation               {#mainpage}
========================

[![DOI](https://zenodo.org/badge/21212519.svg)](https://zenodo.org/badge/latestdoi/21212519)

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

`./configure --enable-rabbitmq; make; make install` will then successfully build the `tacc_stats` executable for many systems.  If Xeon Phi coprocessors are present on your system they can be monitored with the `--enable-mic` flag.  Additionally the configuration options, `--disable-infiniband`, `--disable-lustre`, `--disable-hardware` will disable infiniband, Lustre Filesystem, and Hardware Counter monitoring which are all enabled by default.  Not enabling RabbitMQ will result in a legacy build of `tacc_stats` that relies on the shared filesystem to transmit data.  This mode is not recommended.  If libraries or header files are not found than add their paths to the include and library paths with the `CPPFLAGS` and/or `LDFLAGS` vars as is standard in autoconf based installations.  

There will be a configuration file, `/etc/tacc_stats.conf`, after installation.  This file contains the fields

`SERVER=localhost`

`QUEUE=default`

`PORT=5672`

`FREQ=600`


`SERVER` should be set to the RabbitMQ server, `QUEUE` to the system name, `PORT` to the RabbitMQ port (5672 should be ok), and `FREQ` to the desired sampling frequency in seconds.

An RPM can be built for subpackage deployment using  the `tacc_statsd_systemv.spec` file.  The most straightforward approach to build this is to setup your rpmbuild directory then run

`rpmbuild -ba tacc_statsd_systemv.spec --define 'rmqserver rabbitmqservername' --define 'system systemname'`

where the `rmqserver` will be the RabbitMQ `SERVER` hostname and `system` will be the RabbitMQ `QUEUE` the data is sent to. 
Configuration options may have to be changed within the `tacc_statsd_systemv.spec` file.

After installation the executable `/opt/tacc_statsd/tacc_stats` and SystemV service file `/etc/systemd/system/taccstats.service`, should exist.  If the rpm was used for installation `taccstats` will be `enable`'d to start at boot time and be restart within 10 seconds if it fails for any reason.
`tacc_stats` can be started, stopped, and restarted using `systemctl start taccstats`, `systemctl stop taccstats`, and `systemctl restart taccstats`.

In order to notify `tacc_stats` of a job beginning echo the job id into `/var/run/TACC_jobid`.  It order to notify
it of a job ending echo `-` into `/var/run/TACC_jobid`.  This can be accomplished in the job scheduler prolog and
epilog for example.

#### Job Scheduler Configuration
-------
In order for tacc_stats to correcly label records with JOBIDs it is required that
the job scheduler prolog and epilog contain the lines


`echo $JOBID > jobid_file`  

and

`echo - > jobid_file`

To perform the pickling of this data it is also necessary to
generate an accounting file that contains the following information
in the following format

`JobID|User|Account|Start|End|Submit|Partition|Timelimit|JobName|State|NNodes|ReqCPUS|NodeList`

for example,

1837137|rtevans|project140208|2018-08-01T18:18:51|2018-08-02T11:44:51|2018-07-29T08:05:43|normal|1-00:00:00|jobname|COMPLETED|8|104|c420-[024,073],c421-[051-052,063-064,092-093]

If using SLURM the `sacct_gen.py` script that will be installed with the `tacc_stats` subpackage may be used. 
This script generates a file for each date with the name format `year-month-day.txt`, e.g. `2018-11-01.txt`.

#### `tacc_stats` subpackage
 To install TACC Stats on the machine where data will be processed, analyzed, and the webserver hosted follow these
 steps:
 
1.  Download the package and setup the Python3 virtual environment. TACC Stats is Python3 dependent.
```
$ virtualenv machinename --system-site-packages
$ cd machinename; source bin/activate
$ git clone https://github.com/TACC/tacc_stats
```
`tacc_stats` is a pure Python package.  Dependencies should be automatically downloaded
and installed when installed via `pip`.  The package must first be configured however 
in the `tacc_stats.ini` file.  
2.  The initialization file, `tacc_stats.ini`, controls all the configuration options and has 
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
acct_path       = %(data_dir)s/accounting
pickles_dir     = %(data_dir)s/pickles
archive_dir     = %(data_dir)s/archive
host_name_ext   = %(machine)s.tacc.utexas.edu
batch_system    = SLURM
```
Set these paths as needed. The `accounting_path` will contain an accounting file for each date, e.g. `2018-11-01.txt`. The raw stats data will be stored in the `archive_dir` and processed stats data in the `pickles_dir`.  `machine` should match the system name used in the RabbitMQ server `QUEUE` field and is the RabbitMQ `QUEUE` that the monitoring agent sends the data too.  This is the only field that needs to match settings in the `monitor` subpackage. `host_name_ext` is the extension required to each compute node hostname in order to build a FQDN. This will match to directory names created in the `archive_dir`. 
3.  Install `tacc_stats`
```
$ pip install -e tacc_stats/
```
4.  Start the RabbitMQ server reader in the background, e.g. 
```
$ nohup listend.py > /tmp/listend.log
```
Raw stats files will now be generated in the `archive_dir`.
5.  A PostgreSQL database must be setup on the host.  To do this, after installation of PostgreSQL
and the `tacc_stats` Python module 
```
$ sudo su - postgresql
$ psql
# CREATE DATABASE machinename_db;
# CREATE USER taccstats WITH PASSWORD 'taccstats';
# ALTER ROLE taccstats SET client_encoding TO 'utf8';
# ALTER ROLE taccstats SET default_transaction_isolation TO 'read committed';
# ALTER ROLE taccstats SET timezone TO 'UTC';
# ALTER DATABASE machinename_db OWNER TO taccstats;
# GRANT ALL PRIVILEGES ON DATABASE machinename_db TO taccstats;
# \q
```

then

```
$ python manage.py migrate
```
This will generate a table named `machinename_db` in your database.  

6.  Setup cron jobs to process raw data and ingest into database.  Add the following to your 
cron file
```
*/15 * * * * source /home/rtevans/testing/bin/activate; job_pickles.py; update_db.py > /tmp/ls5_update.log 2>&1
```
7.  Next configure the Apache server (make sure it is installed and the `mod_wsgi` Apache module is installed)
A sample configuration file, `/etc/httpd/conf.d/ls5.conf`, looks like
```
LoadModule wsgi_module /stats/stampede2/lib/python3.7/site-packages/mod_wsgi/server/mod_wsgi-py37.cpython-37m-x86_64-linux-gnu.so
WSGISocketPrefix run/wsgi

<VirtualHost *:80>

ServerAdmin rtevans@tacc.utexas.edu
ServerName stats.webserver.tacc.utexas.edu
ServerAlias stats.webserver.tacc.utexas.edu

WSGIDaemonProcess s2-stats python-home=/stats/stampede2 python-path=/stats/stampede2/tacc_stats:/stats/stampede2/lib/python3.7/site-packages user=rtevans
WSGIProcessGroup s2-stats
WSGIScriptAlias / /tacc_stats/site/tacc_stats_site/wsgi.py process-group=s2-stats
WSGIApplicationGroup %{GLOBAL}

<Directory /stats/stampede2/tacc_stats/tacc_stats/site/tacc_stats_site>
<Files wsgi.py>
Require all granted
</Files>
</Directory>
</VirtualHost>
```
8.  Start up Apache 

### Running `job_pickles.py`
`job_pickles.py` can be run manually by:

    $ ./job_pickles.py [start_date] [end_date] [-dir directory] [-jobids id0 id1 ... idn]

where the 4 optional arguments have the following meaning

  - `start_date`     : the start of the date range, e.g. `"2013-09-25"` (default is today)
  - `end_date`       : the end of the date range, e.g. `"2013-09-26"` (default is `start_date`)
  - `-dir`       : the directory to store pickled dictionaries (default is set in tacc_stats.ini)
  - `-jobids`     : individual jobids to pickle (default is all jobs)
  
No arguments results in all jobs from the previous day getting pickled and stored in the `pickles_dir`
defined in `tacc_stats.ini`. On Stampede argumentless `job_pickles.py` is run every 24 hours as a `cron` job
set-up by the user.


### Pickled data format: generated `job_pickles.py`

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
