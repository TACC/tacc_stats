#!/bin/bash

# README
# This script is used to generate pickles for certain dates.
# Make sure to edit pickle.conf for your specific environment.
# Note that this script will create the pickle for the start
# date and all the dates inbetween but not the end date.
# Also note that the date arguments can be in any format because
# they are converted into the correct format inside the script.

# HOW TO RUN
# ./do_job_pickles.sh 2013-01-01 2013-02-01


set -eux
prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))
export PATH=$PATH:$prog_dir
export PYTHONPATH=$prog_dir

# read the configuration file
source $prog_dir/pickle.conf

# convert dates to format needed YYYY-MM-DD
start_date=$(date --date="$1" +%F)
end_date=$(date --date="$2" +%F)

if [ x"$start_date" = x ] || [ x"$end_date" = x ]; then
    echo "Usage: $prog START_DATE END_DATE" >&2
    exit 1
fi

# go through each date and create pickles
date=$start_date
while [[ $date < $end_date ]]; do
    for hours in 22 23 24 25 26; do
        next_date=$(date --date="$date + $hours hours" +%F)
        if [ $next_date != $date ]; then
            break
        fi
    done

    if [[ $next_date == $date ]]; then
        exit 3
    fi

    mkdir $tmp_dir/$date
    job_pickles.py $tmp_dir/$date $date $next_date
    tar -C $tmp_dir -czf $dst_dir/$date.tar.gz $date
    rm -rf $tmp_dir/$date
    date=$next_date
done
