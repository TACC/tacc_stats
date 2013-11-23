### This file will configure the counter collectors and
### log picklers for a specific system setup.
### The user is expected to supply these fields

## Paths on compute hosts## \
# directory of compute host's raw stats file \
stats_dir=/var/log/tacc_stats
# compute host's lock file for tacc_stats process \
stats_lock=/var/lock/tacc_stats
# file containing jobid \
jobid_file=/var/run/TACC_jobid 

## Paths for persistent log data and pickling
# home directory for presistent stats data 
tacc_stats_home=/scratch/projects/tacc_stats/
# file that contains characterizes all logged jobs
acct_path=/scratch/projects/tacc_stats/accounting/tacc_jobs_completed
# location of host files, labeled by jobid and containing hosts
# used for jobid
host_list_dir=/scratch/projects/tacc/hostfile_logs/
# location to store pickles
pickles_dir=/scratch/projects/tacc_stats/pickles/
python_path=/opt/apps/python/epd/7.3.2/bin/
## Host Name Extension and Batch System (Currently SGE or SLURM)##
host_name_ext=stampede.tacc.utexas.edu
batch_system=SLURM
## Path to lariat data
lariat_path=/scratch/projects/lariatData/

## System specific Schema items. ##
## Chips type and infiniband may need to be
## changed for different systems ## 
########################
## Chip types
# Each chip will need a different counter routine
# for non-architectural events.
# If chip or device is absent it will be skipped
# at run time.
TYPES+="amd64_pmc "
TYPES+="intel_nhm "
TYPES+="intel_wtm "
TYPES+="intel_uncore "
TYPES+="intel_snb "
TYPES+="intel_snb_cbo "
TYPES+="intel_snb_pcu "
TYPES+="intel_snb_imc "
TYPES+="intel_snb_qpi "
TYPES+="intel_snb_hau "
TYPES+="intel_snb_r2pci "
########################
## Infiniband usage
TYPES+="ib "
TYPES+="ib_sw "
TYPES+="ib_ext "
########################
## Lustre filesystem usage (per mount)
# Lustre network usage
TYPES+="llite "
TYPES+="lnet " 
# Lustre stats
TYPES+="mdc "
TYPES+="osc "
#########################
## The following should be linux generic 
# Block specific statistics
TYPES+="block "
# Scheduler accounting (per CPU)
TYPES+="cpu "
# Memory usage (per socket)
TYPES+="mem "
# Network device usage (per device)
TYPES+="net "
# NFS stats
TYPES+="nfs "
# NUMA statistics (per socket)
TYPES+="numa "
# Thread stats?
TYPES+="ps "
# SysV shared memory segment usage
TYPES+="sysv_shm "
# Ram-backed filesystem usage (per mount)
TYPES+="tmpfs "
# Dentry/file/inode cache usage
TYPES+="vfs "
# Virtual memory statistics
TYPES+="vm "

cmake \
-Dstats_dir=${stats_dir} \
-Dstats_lock=${stats_lock} \
-Djobid_file=${jobid_file} \
-Dtacc_stats_home=${tacc_stats_home} \
-Dacct_path=${acct_path} \
-Dhost_list_dir=${host_list_dir} \
-Dpickles_dir=${pickles_dir} \
-Dpython_path=${python_path} \
-Dhost_name_ext=${host_name_ext} \
-Dbatch_system=${batch_system} \
-Dlariat_path=${lariat_path} \
-DTYPES="${TYPES}" \
../
