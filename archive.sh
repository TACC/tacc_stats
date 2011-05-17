#!/bin/bash
# tacc_stats_archive: compress the previous day's tacc_stats data
# and archive for analysis by Cornell (and TACC) people.

PATH=/bin:/usr/bin
umask 0022

prog=$(basename $0)
stats_dir=$1
archive_dir=$2
host_dir=$archive_dir/$(hostname --fqdn)

if [ -z "$stats_dir" -o -z "archive_dir" ]; then
    echo "Usage: ${prog} STATS_DIR ARCHIVE_DIR" >&2
    exit 1
fi

if ! [ -d $stats_dir ]; then
    exit 1
fi

if ! [ -d $host_dir ] && ! mkdir $host_dir; then
    exit 1
fi

now=$(date +%s)
for file in $stats_dir/*; do
    if ! [ -f $file ]; then
        continue
    fi
    base=$(basename $file)
    if ! [[ $base =~ ^[[:digit:]]+$ ]]; then
        continue
    fi
    # Skip if file is less than 1 day old.
    if ((now - base < 86400)); then
        continue
    fi
    if gzip -c $file > $host_dir/$base.gz; then
        rm $file
    fi
done
