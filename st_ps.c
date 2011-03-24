#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include "stats.h"
#include "trace.h"

// $ cat /proc/stat
// cpu ...
// ...
// intr ...
// ctxt 15088509272
// btime 1288194676
// processes 2591587 /* nr_forks */
// procs_running 17
// procs_blocked 0

static void collect_proc_stat(struct stats *ps_stats)
{
  const char *path = "/proc/stat";
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  while (getline(&line, &line_size, file) >= 0) {
    char *key, *rest = line;
    key = strsep(&rest, " ");
    if (*key == 0 || rest == NULL)
      continue;

    if (strncmp(key, "cpu", 3) == 0)
      continue;

    if (strcmp(key, "intr") == 0)
      continue;

    errno = 0;
    unsigned long long val = strtoull(rest, NULL, 0);
    if (errno == 0)
      stats_set(ps_stats, key, val);
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);
}

static void collect_loadavg(struct stats *ps_stats)
{
  const char *path = "/proc/loadavg";
  FILE *file = NULL;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
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

static void collect_ps(struct stats_type *type)
{
  struct stats *ps_stats = NULL;

  ps_stats = get_current_stats(type, NULL);
  if (ps_stats == NULL)
    return;

  collect_proc_stat(ps_stats);
  collect_loadavg(ps_stats);
}

struct stats_type STATS_TYPE_PS = {
  .st_name = "ps",
  .st_collect = &collect_ps,
  .st_schema = (char *[]) {
    "btime", "ctxt", "processes", "load_1", "load_5", "load_15", "nr_running", "nr_threads", NULL,
  },
};
