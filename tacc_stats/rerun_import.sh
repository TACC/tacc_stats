for i in $(seq 30 20 900);

do 
   j=$(($i-20));
#   echo `date --date "today - $i day" +\%Y-\%m-\%d`
   source /home/sharrell/ls6_ts/bin/activate; /home/sharrell/ls6_ts/tacc_stats/tacc_stats/dbload/sync_timedb.py `date --date "today - $i day" +\%Y-\%m-\%d` `date --date "today - $j day" +\%Y-\%m-\%d`
   echo
done
