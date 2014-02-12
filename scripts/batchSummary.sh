#!/bin/bash
# This script creates batch summary reports for tacc_stats
# $./batchSummary.sh 2013-06 Lonestar > /dev/shm/logs/batchSummary/Lonestar/2013-06.o 2> /dev/shm/logs/batchSummary/Lonestar/2013-06.e &
# arg[1] - date         YYYY-MM-DD
# arg[2] - hostname     Lonestar

#export PYTHONPATH=/data/scratch/jsonpicklelib/lib/python:/data/scratch/jsonpicklelib/lib/python/jsonpicklext
source /user/xdtas/kmarcus2/notes.txt

if [ ${2,,} == "rush" ]
then
        summary=/user/xdtas/kmarcus2/summary_rush_slurm.py
elif [ ${2,,} == "stampede" ]
then
        export PYTHONPATH=/data/scratch/tacc_stats_billbarth/monitor
        summary=/user/xdtas/kmarcus2/summary_stampede_slurm.py
else
        summary=/user/xdtas/kmarcus2/summary.py
fi

for pickleTar in /data/scratch/${2}/pickles/${1}*
do
        echo $pickleTar
        mkdir -p /dev/shm/archive/${2}
        tar xf $pickleTar -C /dev/shm/archive/${2}
        pickleDirDate=`basename $pickleTar`
        pickleDirDate=${pickleDirDate%%.*}
        mkdir -p /dev/shm/json/${2}/$pickleDirDate-json
        mkdir -p /dev/shm/pickles/${2}/${1}
        for pickleFile in /dev/shm/archive/${2}/$pickleDirDate/*
        do
                echo $pickleFile
                cp $pickleFile /dev/shm/pickles/${2}/${1}
                mkdir -p /dev/shm/logs/summary/${2}
                python $summary /dev/shm/pickles/${2}/${1} /data/scratch/${2}/lariatData > /dev/shm/json/${2}/$pickleDirDate-json/`basename $pickleFile`.json 2>>/dev/shm/logs/summary/${2}/${1}.e
                rm /dev/shm/pickles/${2}/${1}/*
        done
        rm -r /dev/shm/archive/${2}/$pickleDirDate
        rm -r /dev/shm/pickles/${2}/${1}
        tar czf /dev/shm/json/${2}/$pickleDirDate-json.tar.gz --directory=/dev/shm/json/${2} $pickleDirDate-json
        #rm -r /dev/shm/json/$2/$pickleDirDate-json
done

# copy the tar.gz files over to ifs, do not remove the directories because these need to be put into
# mongo (this script and the mongo script are being called by the update.sh scripts. The update script
# will then clean up these directories after the mongo insert is done.  This is done so that files are
# read locally and not on ifs which is slower.
cp /dev/shm/json/${2}/*.tar.gz /ifs/projects/xdtas/summaries/${2,,}/ && rm /dev/shm/json/${2}/*.tar.gz
mv /data/scratch/${2}/pickles/${1}* /ifs/projects/xdtas/pickles/${2,,}/
