#!/bin/bash
while true
do
    /bin/rsync -avq -e 'ssh -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no' sharrell@staff.stampede3.tacc.utexas.edu:/home1/01623/sharrell/s3_acct_logs/* /hpcperfstats/accounting/
    sleep 3600
done
