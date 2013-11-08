#!/bin/bash

date=$(date --date=yesterday +%F)
tar -zxvf /hpc/tacc_stats/stampede/pickles/${date}.tar.gz -C /hpc/tacc_stats_site/stampede/pickles/

python /home/rtevans/tacc_stats/analyze/site/update_db.py
