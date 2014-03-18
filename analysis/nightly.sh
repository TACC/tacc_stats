#!/bin/bash
wd='/home/rtevans/tacc_stats/bin'

if [ "$1" == "" ]; then
  y=`date -d yesterday +%Y-%m-%d`
else
  y=$1
fi

tsd='/hpc/tacc_stats_site/stampede/pickles/'
od=${wd}/nightlies/${y}

if [ ! -d $od ]; then
    mkdir -p $od
else
    echo "$od already exists"
fi

export PYTHONUNBUFFERED=yes
export PYTHONPATH='/home/rtevans/tacc_stats/lib':${PYTHONPATH}
cd ${od}

#${wd}/nightly.py -p 2 ${tsd}/${y} > ${od}/${y}.log 2>&1
#${wd}/job_sweeper.py -p 2 -start ${y} -end ${y} -t 1.0 -test HighCPI
${wd}/job_sweeper.py -p 2 -start ${y} -end ${y} -t 1.0 -test Imbalance
${wd}/job_sweeper.py -p 2 -start ${y} -end ${y} -t 0.999 -test Idle
${wd}/job_sweeper.py -p 2 -start ${y} -end ${y} -t 0.001 -test LowFLOPS
${wd}/job_sweeper.py -p 2 -start ${y} -end ${y} -t 0.001 -N 2 -test Catastrophe
