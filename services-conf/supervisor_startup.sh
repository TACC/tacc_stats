#!/bin/sh


chmod -c 755 /hpcperfstats/
# make directories if they are not there
mkdir -pv /hpcperfstats/accounting
mkdir -pv /hpcperfstats/archive
mkdir -pv /hpcperfstats/daily_archive
mkdir -pv /hpcperfstats/logs
chown -R hpcperfstats:hpcperfstats /hpcperfstats/* 
cp /hpcperfstats/.ssh/id* /home/hpcperfstats/.ssh/
chown -R hpcperfstats:hpcperfstats /home/hpcperfstats/.ssh
chmod -R 0600  /home/hpcperfstats/.ssh/*

/usr/bin/supervisord



