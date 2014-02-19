#!/bin/bash

# Copyright (C) 2014 State University of New York at Buffalo
# Authors: Kyle Marcus
#          Joseph P White <jpwhite4@buffalo.edu>

CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SUPREMM_CONFIG_PATH=${SUPREMM_CONFIG_PATH:-${CURDIR}/../etc}
TRANSFER_SCRIPT=$CURDIR/rawTaccStatsTarTransfer.sh
unset CURDIR

function usage
{
    echo "usage $0 MACHINENAME"
    echo " process the tacc_stats records for machine MACHINENAME."
    echo " the machine must have a valid configuration file located in"
    echo " ${SUPREMM_CONFIG_PATH}/MACHINENAME.conf"
}

function gentimedirlist
{
    export TZ=utc0

    # Note only generate the datestamp once to avoid race condition in date
    # change between invocations

    now=$(date +%Y/%m/%d)

    for (( i = 3; i > 0; i-- ));
    do
        echo -n " "$(date -d "$now - $i day" +%Y/%m/%d)
    done
}

# Source global settings
source ${SUPREMM_CONFIG_PATH}/supremm.conf

# Try to source machine-specific settings
if [ -e ${SUPREMM_CONFIG_PATH}/$1.conf ];
then
    source ${SUPREMM_CONFIG_PATH}/$1.conf
else
    usage
    exit 1
fi

CONTROLPATH="$HOME/.ssh/ctl/$$-%L-%r@%h:%p"
RSYNCRSH="ssh -i ${REMOTE_ID} -o ControlPath=${CONTROLPATH}"

# Determine processing date
d=$(date -d 'now -2 days' +%F)

# Create initial ssh connection
mkdir -p $(dirname ${CONTROLPATH})
ssh -i ${REMOTE_ID} -MnNf -o ControlMaster=yes -o ControlPersist=yes -o ControlPath=${CONTROLPATH} ${REMOTE_LOGIN}

if [ -n "${REMOTE_ACCOUNTING_PATH}" ];
then
    # Update accounting file
    date
    mkdir -p ${LOCAL_MIRROR_PATH}/accounting
    rsync -v -t -z -e "${RSYNCRSH}" ${REMOTE_LOGIN}:${REMOTE_ACCOUNTING_PATH} ${LOCAL_MIRROR_PATH}/accounting
fi

if [ -n "${REMOTE_HOSTFILE_PATH}" ];
then
    # Update hostfiles
    date
    cd ${LOCAL_HOSTFILE_PATH}
    echo "cd ${REMOTE_HOSTFILE_PATH} && find $(gentimedirlist) -print -depth | cpio -o" | ssh -i ${REMOTE_ID} -o ControlPath=${CONTROLPATH} ${REMOTE_LOGIN} "bash -s" | cpio -i -d
    cd -
fi

if [ -n "${REMOTE_LARIAT_PATH}" ];
then
    # Update lariat data
    date
    rsync -v -t -r -e "${RSYNCRSH}" ${REMOTE_LOGIN}:${REMOTE_LARIAT_PATH} ${LOCAL_MIRROR_PATH}
fi

### TODO
scp -i ${REMOTE_ID} -o ControlPath=${CONTROLPATH} ${TRANSFER_SCRIPT} ${REMOTE_LOGIN}:./rawTaccStatsTarTransfer.sh
ssh -i ${REMOTE_ID} -o ControlPath=${CONTROLPATH} ${REMOTE_LOGIN} "./rawTaccStatsTarTransfer.sh ${REMOTE_ARCHIVE_PATH}" | tar xfk - -C ${LOCAL_MIRROR_PATH}/archive
###


if [ -n "${REMOTE_PICKLE_PATH}" ];
then
    # Retreive the pickle files from the remote machine
    rsync -v -t -e "${RSYNCRSH}" ${REMOTE_LOGIN}:${REMOTE_PICKLE_PATH}/${d}.tar.gz ${LOCAL_MIRROR_PATH}/pickles/${d}.tar.gz
fi

# close the ssh session
ssh -O exit -o ControlPath=${CONTROLPATH} ${REMOTE_LOGIN}

if [ -z "${REMOTE_PICKLE_PATH}" ];
then
    # create the pickle for today, pickles are stored in ${LOCAL_MIRROR_PATH}/pickles
    date
    do_job_pickles_cron.sh ${LOCAL_MIRROR_PATH}/pickle.conf # TODO
fi

# create summaries, for each date create a .tar.gz file that is put into ifs
LOGDIR=${LOG_PATH}/batchSummary/${MACHINE_NAME}
mkdir -p ${LOGDIR}

JSONDIR=${JSON_SCRATCH_PATH}/${MACHINE_NAME}
# TODO the jsondir is specified here, and used in batchSummary and summartConvert
#      yet it is hardcoded in batchSummary

batchSummary.sh ${d} ${MACHINE_NAME} > ${LOGDIR}/${d}.o 2> ${LOGDIR}/${d}.e

# put sumaries into mongo
MLOGDIR=${LOG_PATH}/mongo/${MACHINE_NAME}
mkdir -p ${MLOGDIR}
summaryConvertToMongo.py ${JSONDIR}/${d}-json ${MACHINE_NAME} >${MLOGDIR}/${d}.o 2>${MLOGDIR}/${d}.e

# Clean up 
rm -r ${JSONDIR}/${d}-json
