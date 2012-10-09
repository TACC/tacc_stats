#!/bin/bash

wd=/work/00564/bbarth/tacc_stats/analyze/process_pickles
if [ "$1" == "" ]; then
  y=`date -d yesterday +%Y-%m-%d`
else
  y=$1
fi
tsd=/scratch/projects/tacc_stats/pickles
jd=${wd}/nightly_jobs
nf=${tsd}/${y}.tar.gz
od=${wd}/nightlies/${y}

cd $wd

if [ -f $nf ]; then
  if [ ! -d $jd ]; then
    mkdir $jd
    cd $jd
    tar xf $nf
  fi
  
  cd $wd

  if [ ! -d $od ]; then
    mkdir -p $od
  fi
  module load python

  export PYTHONUNBUFFERED=yes

  ./nightly.py -o $od -p 32 1.0 ${jd}/${y} > ${od}/nightly-${y}.log 2>&1
else
  echo "$nf not available"
  exit 1
fi
