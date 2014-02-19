#!/bin/bash
# This script creates batch summary reports for tacc_stats
# $./batchSummary.sh 2013-06 Lonestar > ${LOG_PATH}/batchSummary/Lonestar/2013-06.o 2> ${LOG_PATH}/batchSummary/Lonestar/2013-06.e &
# arg[1] - date         YYYY-MM-DD
# arg[2] - hostname     Lonestar

CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SUPREMM_CONFIG_PATH=${SUPREMM_CONFIG_PATH:-${CURDIR}/../etc}
unset CURDIR

function usage
{
    echo "usage $0 DATE MACHINENAME"
    echo " create batch summary reports for tacc_stats for date DATE"
    echo " the machine must have a valid configuration file located in"
    echo " ${SUPREMM_CONFIG_PATH}/MACHINENAME.conf"
}

# Source global settings
source ${SUPREMM_CONFIG_PATH}/supremm.conf

# Try to source machine-specific settings
if [ -e ${SUPREMM_CONFIG_PATH}/$2.conf ];
then
    source ${SUPREMM_CONFIG_PATH}/$2.conf
else
    usage
    exit 1
fi

# TODO Stampede uses a different pythonpath

for pickleTar in ${LOCAL_MIRROR_PATH}/pickles/${1}*
do
        JSON_SCRATCH=${JSON_SCRATCH_PATH}/${MACHINE_NAME}
        PCKL_SCRATCH=${PICKLE_SCRATCH_PATH}/${MACHINE_NAME}/${1}
        ARCV_SCRATCH=${ARCHIVE_SCRATCH_PATH}/${MACHINE_NAME}

        echo $pickleTar
        mkdir -p ${ARCV_SCRATCH}
        tar xf $pickleTar -C ${ARCV_SCRATCH}
        pickleDirDate=`basename $pickleTar`
        pickleDirDate=${pickleDirDate%%.*}
        mkdir -p ${JSON_SCRATCH}/$pickleDirDate-json
        mkdir -p ${PCKL_SCRATCH}
        for pickleFile in ${ARCV_SCRATCH}/$pickleDirDate/*
        do
                echo $pickleFile
                cp $pickleFile ${PCKL_SCRATCH}
                mkdir -p ${LOG_PATH}/summary/${2}
                ${SUMMARY_SCRIPT} ${PCKL_SCRATCH} ${LOCAL_MIRROR_PATH}/lariatData > ${JSON_SCRATCH}/$pickleDirDate-json/`basename $pickleFile`.json 2>>${LOG_PATH}/summary/${2}/${1}.e
                rm ${PCKL_SCRATCH}/*
        done
        rm -r ${ARCV_SCRATCH}/$pickleDirDate
        rm -r ${PCKL_SCRATCH}
        tar czf ${JSON_SCRATCH}/$pickleDirDate-json.tar.gz --directory=${JSON_SCRATCH} $pickleDirDate-json

done

# copy the tar.gz files over to ifs, do not remove the directories because these need to be put into
# mongo (this script and the mongo script are being called by the update.sh scripts. The update script
# will then clean up these directories after the mongo insert is done.  This is done so that files are
# read locally and not on ifs which is slower.
cp ${JSON_SCRATCH}/*.tar.gz ${PROCESSED_SUMMARY_PATH}/ && rm ${JSON_SCRATCH}/*.tar.gz
mv ${LOCAL_MIRROR_PATH}/pickles/${1}* ${PROCESSED_PICKLES_PATH}/
