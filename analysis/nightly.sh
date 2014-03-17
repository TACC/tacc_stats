#!/bin/bash
wd='/Users/rtevans/tacc_stats/bin'

if [ "$1" == "" ]; then
  y=`date -d yesterday +%Y-%m-%d`
else
  y=$1
fi

tsd='/Users/rtevans/pickles/'
od=${wd}/nightlies/${y}

if [ ! -d $od ]; then
    mkdir -p $od
else
    echo "$od already exists"
fi

export PYTHONUNBUFFERED=yes
export PYTHONPATH='/Users/rtevans/tacc_stats/lib':${PYTHONPATH}
cd ${od}
${wd}/nightly.py -p 2 ${tsd}/${y} > ${od}/${y}.log 2>&1

