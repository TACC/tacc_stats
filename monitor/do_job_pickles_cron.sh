#!/bin/bash

# README
# This script should be used inside a cron job to create pickles
# every day. It will create one YYYY-MM-DD.tar.gz file inside the
# $dst_dir which is specified in the pickle.conf file. Currently it
# is set up so that it creates the pickle for the day 2 days from
# the current date. This can be changed to what ever fits your needs.

# ARGUMENTS
# There is 1 optional argument. This argument is the file path to
# the configuration file that you want to use. If it is not specified
# then the default pickle.conf file will be used

# HOW TO RUN
# ./do_job_pickles_cron.sh {conf file path}

set -eu

prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))

export PATH=$prog_dir:$PATH
export PYTHONPATH=$prog_dir:${PYTHONPATH:-}

# read the configuration file
if [ $# -eq 1 ] && [ -f $1 ]
then
	source $1
else
	source $prog_dir/pickle.conf
fi


# get the date's
#d0=$(date --date=yesterday +%F)
#d1=$(date --date=today +%F)
d0=$(date -d 'now -2 days' +%F)
d1=$(date -d 'now -1 days' +%F)

# redirect the output
exec 0< /dev/null
exec 1> $tmp_dir/$prog.out.$d0.$d1
exec 2> $tmp_dir/$prog.err.$d0.$d1

set -x

mkdir $tmp_dir/$d0
$prog_dir/job_pickles.py $tmp_dir/$d0 $d0 $d1
tar -C $tmp_dir -czf $dst_dir/$d0.tar.gz $d0
rm -r $tmp_dir/$d0
