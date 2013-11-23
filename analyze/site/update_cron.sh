#!/bin/bash

set -eu

prog=$(basename $0)
prog_dir=$(readlink -f $(dirname $0))

export PATH=/opt/apps/python/epd/7.3.2/bin/:$prog_dir:$PATH

date=$(date --date=yesterday +%F)

exec 0< /dev/null
exec 1> $prog.out.$date
exec 2> $prog.err.$date

set -x

python $prog_dir/tar.py
python $prog_dir/update_db.py yesterday
python $prog_dir/ls4_update_db.py yesterday