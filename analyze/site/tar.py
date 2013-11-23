#!/usr/bin/env python

import os 
from subprocess import Popen, PIPE


tar_dir = '/hpc/tacc_stats/stampede/pickles/'
untar_dir = '/hpc/tacc_stats_site/stampede/pickles/'

for tarball in os.listdir(tar_dir):

    if tarball.split(".")[0] in os.listdir(untar_dir): continue
    tar_path = str(os.path.join(tar_dir,tarball))
    print tar_path
    p = Popen(["/bin/tar -zxvf " + tar_path + " -C " + untar_dir],shell=True)
    p.communicate()


tar_dir = '/hpc/tacc_stats/lonestar/pickles/'
untar_dir = '/hpc/tacc_stats_site/lonestar/pickles/'

for tarball in os.listdir(tar_dir):

    if tarball.split(".")[0] in os.listdir(untar_dir): continue
    tar_path = str(os.path.join(tar_dir,tarball))
    print tar_path
    p = Popen(["/bin/tar -zxvf " + tar_path + " -C " + untar_dir],shell=True)
    p.communicate()
