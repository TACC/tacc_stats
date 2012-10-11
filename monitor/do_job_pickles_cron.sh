#!/bin/bash
set -eu

prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))

export PATH=/opt/apps/python/2.7.1/bin:/opt/apps/python/2.7.1/modules/bin:$prog_dir:$PATH
export LD_LIBRARY_PATH=/opt/apps/python/2.7.1/lib:/opt/apps/python/2.7.1/lib:/opt/apps/pgi7_2/mvapich/1.0.1/lib:/opt/apps/pgi7_2/mvapich/1.0.1/lib/shared:/opt/apps/pgi/7.2-5/linux86-64/7.2-5/libso:/opt/ofed/lib64:/opt/lam/gnu/lib:/opt/apps/binutils-amd/070220/lib64:/opt/apps/gcc_amd/4.4.5/lib64:${LD_LIBRARY_PATH:-}
export PYTHONPATH=/opt/apps/python/2.7.1/modules/lib/python:/opt/apps/python/2.7.1/lib:$prog_dir:${PYTHONPATH:-}

tmp_dir=${tmp_dir:-/dev/shm/}
dst_dir=${dst_dir:-/scratch/projects/tacc_stats/pickles/}

d0=$(date --date=yesterday +%F)
d1=$(date --date=today +%F)

exec 0< /dev/null
exec 1> $tmp_dir/$prog.out.$d0.$d1
exec 2> $tmp_dir/$prog.err.$d0.$d1

set -x

mkdir $tmp_dir/$d0
$prog_dir/job_pickles.py $tmp_dir/$d0 $d0 $d1
tar -C $tmp_dir -czf $dst_dir/$d0.tar.gz $d0
rm -r $tmp_dir/$d0
