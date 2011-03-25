#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include "stats_aggr.h"
#include "trace.h"

int main(int argc, char *argv[])
{
  time_t begin, end, step;
  struct stats_aggr sa;

  if (argc < 4)
    FATAL("usage\n");

  begin = strtol(argv[1], NULL, 0);
  end = strtol(argv[2], NULL, 0);
  step = strtol(argv[3], NULL, 0);

  stats_aggr_init(&sa, NULL, begin, end, step);

  /* Monkey with flags. */
  sa.sa_flags[0] = SF_EVENT | 48;

  time_t time;
  val_t val;
  while (scanf("%ld %llu", &time, &val) == 2)
    stats_aggr(&sa, time, &val);
  stats_aggr_rewind(&sa);

  stats_aggr_print(stdout, &sa, "%s", "DEV", "\t", "\n");

  return 0;
}
