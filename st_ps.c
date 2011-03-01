#define _GNU_SOURCE
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include "stats.h"
#include "trace.h"

void read_loadavg(void)
{
  const char *path = "/proc/loadavg";
  FILE *file = NULL;
  struct stats *ps_stats = NULL;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  ps_stats = get_current_stats(ST_PS, NULL);
  if (ps_stats == NULL) {
    ERROR("cannot set ps_stats: %m\n");
    goto out;
  }

  unsigned long long load[3][2];
  unsigned long long nr_running = 0, nr_threads = 0;

  memset(load, 0, sizeof(load));

  /* Ignore last_pid (sixth field). */
  if (fscanf(file, "%llu.%llu %llu.%llu %llu.%llu %llu/%llu",
             &load[0][0], &load[0][1],
             &load[1][0], &load[1][1],
             &load[2][0], &load[2][1],
             &nr_running, &nr_threads) <= 0) {
    /* XXX */
    goto out;
  }

  stats_set(ps_stats, "load_1",  load[0][0] * 100 + load[0][1]);
  stats_set(ps_stats, "load_5",  load[1][0] * 100 + load[1][1]);
  stats_set(ps_stats, "load_15", load[2][0] * 100 + load[2][1]);

  stats_set(ps_stats, "nr_running", nr_running);
  stats_set(ps_stats, "nr_threads", nr_threads);

 out:
  if (file != NULL)
    fclose(file);
}
