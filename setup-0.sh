#!/bin/bash

mkdir /var/log/tacc_stats
touch /var/log/tacc_stats/0
ln -s /var/log/tacc_stats/0 /var/run/tacc_stats_current

~jhammond/tacc_stats/tacc_stats
