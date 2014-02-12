#!/bin/bash

echo nightly.py
./nightly.py 1.0 'jobs2/2012-09-03/2791518'

echo imbalance.py
./imbalance.py 1.0 amd64_core SSE_FLOPS 'jobs2/2012-09-03/2791518'

echo masterplot.py
./masterplot.py 'jobs2/2012-09-03/2791518'

echo uncorrelated.py
./uncorrelated.py 1.0 amd64_core SSE_FLOPS amd64_core DCSF 'jobs2/2012-09-03/2791518'

echo memusage.py
./memusage.py 'jobs2/2012-09-03/2791518'

echo adjust.py
./adjust.py amd64_core SSE_FLOPS 'jobs2/2012-09-03/2791518'

echo htrate.py
./htrate.py 'jobs2/2012-09-03/2791518'

echo dump_csv_key.py
./dump_csv_key.py amd64_core SSE_FLOPS 'jobs2/2012-09-03/2791518'

echo plotkey.py
./plotkey.py llite open 'jobs2/2012-09-03/2791518'