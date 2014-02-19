#!/bin/bash

set -e

function usage
{
    echo "usage $0 MACHINENAME"
    echo " validate the settings in the machine configuration file:"
    echo " ${SUPREMM_CONFIG_PATH}/MACHINENAME.conf"
}

function loadconfig
{
    if [ ! -e $1 ];
    then
        echo "Error config file $1 missing" >&2
    fi
    source $1
}

function checkmkdir
{
    if [ ! -d "$1" ];
    then
        # This directory doesn't exist: try the next level up
        checkmkdir $(dirname "$1")
        return $?
    fi

    if [ -x "$1" -a -w "$1" ];
    then
        return 1
    else
        return 0
    fi
}

function checkdir
{
    val=${!1}

    if [ -z "$val" ]; then
        echo "Value missing for \$$1"
        return
    fi

    if checkmkdir $val
    then
        echo "Error: $1 unable to make or write to directory $val"
    fi
}

if [ -z "$1" ];
then
    usage
    exit 1
fi

CURDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SUPREMM_CONFIG_PATH=${SUPREMM_CONFIG_PATH:-${CURDIR}/../etc}
unset CURDIR

if [ ! -d ${SUPREMM_CONFIG_PATH} ]; then
    echo "Error \"${SUPREMM_CONFIG_PATH}\" does not exist" >&2
    exit 1
fi

# check that the configuration files can be loaded
# will exit if they are not found or can't be loaded

loadconfig ${SUPREMM_CONFIG_PATH}/supremm.conf
loadconfig ${SUPREMM_CONFIG_PATH}/$1.conf

# Check that the config settings are specifed and the
# directories exist. Carry on if a directory is absent so
# that all failures are listed.

checkdir LOCAL_MIRROR_PREFIX
checkdir LOG_PATH
checkdir RAM_DISK_PATH
checkdir JSON_SCRATCH_PATH
checkdir LOCAL_MIRROR_PATH
checkdir PROCESSED_SUMMARY_PATH
checkdir PROCESSED_PICKLES_PATH

# Check that the remote ssh settings work (if they are set)
if [ -n "$REMOTE_LOGIN" ];
then
    if ! ssh -n -i $REMOTE_ID $REMOTE_LOGIN true > /dev/null 2>&1
    then
        echo "Error could not run command on remote host"
    fi
fi

