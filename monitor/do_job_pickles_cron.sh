#!/bin/bash

# README
# This script should be used inside a cron job to create pickles
# every day. It will create one YYYY-MM-DD.tar.gz file inside the
# $dst_dir which is specified in the pickle.conf file.

# ARGUMENTS
# none

# HOW TO RUN
# ./do_job_pickles_cron.sh

set -eu

prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))

export PATH=$prog_dir:$PATH
export PYTHONPATH=$prog_dir:${PYTHONPATH:-}

# read the configuration file
source $prog_dir/pickle.conf

# get todays and yesterday's date
d0=$(date --date=yesterday +%F)
d1=$(date --date=today +%F)

# redirect the output
exec 0< /dev/null
exec 1> $tmp_dir/$prog.out.$d0.$d1
exec 2> $tmp_dir/$prog.err.$d0.$d1

set -x

mkdir $tmp_dir/$d0
$prog_dir/job_pickles.py $tmp_dir/$d0 $d0 $d1
tar -C $tmp_dir -czf $dst_dir/$d0.tar.gz $d0
rm -r $tmp_dir/$d0
