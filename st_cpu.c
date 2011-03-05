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

static void collect_proc_stat_cpu(struct stats_type *type, char *cpu, char *rest)
{
  /* Ignore the totals line and anything not matching [0-9]+. */
  char *s = cpu;

  if (*s == 0)
    return;

  for (; *s != 0; s++)
    if (!isdigit(*s))
      return;

  struct stats *cpu_stats = get_current_stats(type, cpu);
  if (cpu_stats == NULL)
    return;

  unsigned long long user = 0, nice = 0, system = 0, idle = 0,
    iowait = 0, irq = 0, softirq = 0, steal = 0;

  sscanf(rest, "%llu %llu %llu %llu %llu %llu %llu %llu",
         &user, &nice, &system, &idle,
         &iowait, &irq, &softirq, &steal);

  stats_set(cpu_stats, "user", user);
  stats_set(cpu_stats, "nice", nice);
  stats_set(cpu_stats, "system", system);
  stats_set(cpu_stats, "idle", idle);
  stats_set(cpu_stats, "iowait", iowait);
  stats_set(cpu_stats, "irq", irq);
  stats_set(cpu_stats, "softirq", softirq);
  stats_set(cpu_stats, "steal", steal);
}

static void collect_proc_stat(struct stats_type *type)
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

    if (strncmp(key, "cpu", 3) != 0)
      continue;

    collect_proc_stat_cpu(type, key + 3, rest);
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);
}

struct stats_type ST_CPU_TYPE = {
  .st_name = "ST_CPU",
  .st_collect = &collect_proc_stat,
  .st_schema = (char *[]) {
    "user", "nice", "system", "idle", "iowait", "irq", "softirq", NULL,
  },
};
