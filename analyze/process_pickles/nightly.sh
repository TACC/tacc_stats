#!/bin/bash

d=`date +%Y-%m-%d`
y=`date -d yesterday +%Y-%m-%d`

cd /work/00654/bbarth/tacc_stats/analyze/process_pickles/

mkdir -p $d

module load python

export PYTHONUNBUFFERED=yes

time ./nightly.py -o $y -p 32 1.0 "jobs/$y" > nightly-${d}.log 2>&1 
