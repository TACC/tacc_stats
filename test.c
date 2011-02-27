#define _GNU_SOURCE
#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include "stats.h"
#include "trace.h"

struct stats {
  const char *id;
};

struct stats *get_current_stats(int type, const char *id)
{
  if (id == NULL)
    id = "-"; /* XXX */

  TRACE("get_current_stats %s %s\n", st_name[type], id);
  return (struct stats*) id;
}

void stats_set(struct stats *st, char *key, unsigned long long val)
{
  const char *id = (const char*) st;
  TRACE("stats_set %s %s %llu\n", id, key, val);
}

void stats_set_unit(struct stats *st, char *key, unsigned long long val, const char *unit)
{
  const char *id = (const char*) st;
  unsigned long long mult = 1;

  if (strcasecmp(unit, "KB") == 0)
    mult = 1ULL << 10;
  else if (strcasecmp(unit, "MB") == 0)
    mult = 1ULL << 20;
  else if (strcasecmp(unit, "GB") == 0)
    mult = 1ULL << 30;
  else if (strcasecmp(unit, "TB") == 0)
    mult = 1ULL << 40;
  else if (strlen(unit) != 0)
    ERROR("unknown unit `%s'\n", unit);

  TRACE("stats_set_unit %s %s %llu %s %llu\n", id, key, val, unit, mult);
}

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
