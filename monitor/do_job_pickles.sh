#!/bin/bash
set -eux

prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))
export PATH=$PATH:$prog_dir
export PYTHONPATH=$PYTHONPATH:$prog_dir

tmp_dir=${tmp_dir:-/dev/shm/}
dst_dir=${dst_dir:-/scratch/projects/tacc_stats/pickles/}

arg_start_date=${1:-}
arg_end_date=${2:-}
echo $arg_start_date
start_date=$(date --date="$arg_start_date" +%F)
end_date=$(date --date="$arg_end_date" +%F)

if [ x"$start_date" = x ] || [ x"$end_date" = x ]; then
    echo "Usage: $prog START_DATE END_DATE" >&2
    exit 1
fi

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
