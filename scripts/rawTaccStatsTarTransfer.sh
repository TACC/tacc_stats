#!/bin/bash

archive=${1:-/scratch/projects/tacc_stats/archive}
cd $archive
tf=`mktemp`

lscmd=ls
if which lfs > /dev/null;
then
    lscmd="lfs ls"
fi

for dir in `$lfscmd`
do
	echo ${dir}/`$lfscmd $dir | sort -r | head -1` >> $tf
done

tar -cf - --directory=$archive -T $tf

rm $tf
