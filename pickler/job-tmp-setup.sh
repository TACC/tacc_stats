#!/bin/bash

TS_TMP_DIR=${TS_TMP_DIR:-/tmp/TS}

rm -rf $TS_TMP_DIR
mkdir -p $TS_TMP_DIR
# mkdir $TS_TMP_DIR/host_lists
ln -s /share/sge6.2/default/tacc/hostfile_logs $TS_TMP_DIR/prolog_host_lists
ln -s /scratch/projects/tacc_stats/archive $TS_TMP_DIR/stats
cp ~/tacc_stats_data/accounting $TS_TMP_DIR/accounting                               
# cp ~/tacc_stats_data/prolog_hostfile.2255593.nj13737 $TS_TMP_DIR/host_lists/2255593
