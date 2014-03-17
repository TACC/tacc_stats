#!/bin/bash
wd='/hpc/tacc_stats_site/tacc_stats/bin'

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
export PYTHONPATH='/hpc/tacc_stats_site/tacc_stats/lib':${PYTHONPATH}
cd ${od}
${wd}/nightly.py -p 2 ${tsd}/${y} > ${od}/${y}.log 2>&1

