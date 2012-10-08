#!/bin/bash

wd=/work/00564/bbarth/tacc_stats/analyze/process_pickles
d=`date +%Y-%m-%d`
y=`date -d yesterday +%Y-%m-%d`
tsd=/scratch/projects/tacc_stats/pickles
jd=${wd}/nightly_jobs
nf=${tsd}/${y}.tar.gz

cd $wd

if [ -f $nf ]; then
  mkdir $jd
  cd $jd
  tar xf $nf

  cd $wd
  mkdir -p $wd/$y
  module load python

  export PYTHONUNBUFFERED=yes

  time ./nightly.py -o ${wd}/$y -p 32 1.0 "jobs/$y" > nightly-${y}.log 2>&1
else
  echo "$nf not available"
  exit 1
fi
