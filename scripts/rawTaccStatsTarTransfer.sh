#!/bin/bash

archive=/scratch/projects/tacc_stats/archive/
cd $archive
tf=`mktemp`

for dir in `lfs ls`
do
	echo ${dir}/`lfs ls $dir | sort -r | head -1` >> $tf
done

#tar -cf ${SCRATCH}/tacc_stats-raw_update.tar --directory=$archive -T $tf
tar -cf - --directory=$archive -T $tf

rm $tf
