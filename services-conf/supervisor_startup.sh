#!/bin/sh


# make directories if they are not there
mkdir -pv /hpcstats/accounting
mkdir -pv /hpcstats/archive
mkdir -pv /hpcstats/daily_archive
mkdir -pv /hpcstats/logs
chmod 777 -R /hpcstats/

/usr/bin/supervisord



