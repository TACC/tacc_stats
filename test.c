#define _GNU_SOURCE
#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include "stats.h"
#include "trace.h"

int main(int argc, char *argv[])
{
  // uname()

  read_proc_stat();
  read_loadavg();
  read_meminfo();
  read_vmstat();

  // /proc/schedstat
  // /proc/diskstats
  // /proc/net/dev read_net_dev()
  // /proc/net/rpc/nfs
  // /proc/net/sockstat

  // read_mlx4()
  // read_lustre()

  read_jobid();

  return 0;
}
