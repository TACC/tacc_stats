#define _GNU_SOURCE
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include "stats.h"
#include "trace.h"

#define NUMA_BASE_PATH "/sys/devices/system/node"

static void read_meminfo_node(struct stats *stats, char *node)
{
  char *path = NULL;
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  if (asprintf(&path, "%s/node%s/meminfo", NUMA_BASE_PATH, node) < 0) {
    ERROR("cannot create path: %m\n");
    goto out;
  }

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  while (getline(&line, &line_size, file) >= 0) {
    char key[81], unit[81];
    unsigned long long val = 0;

    key[0] = 0;
    unit[0] = 0;
    if (sscanf(line, "Node %*d %80[^:]: %llu %80s", key, &val, unit) < 2)
      continue;

    if (key[0] == 0)
      continue;

    stats_set_unit(stats, key, val, unit);
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);
  free(path);
}

static void read_meminfo(struct stats_type *type)
{
  const char *base_path = NUMA_BASE_PATH;
  DIR *dir = NULL;

  dir = opendir(base_path);
  if (dir == NULL)
    goto out;

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (strncmp(ent->d_name, "node", 4) != 0)
      continue;

    const char *node = ent->d_name + 4;

    /* Ignore anything not matching [0-9]+. */
    char *s = node;
    if (*s == 0)
      continue;
    for (; *s != 0; s++)
      if (!isdigit(*s))
        continue;

    struct stats *stats = get_current_stats(type, node);
    if (stats == NULL) {
      ERROR("cannot get node_stats: %m\n");
      continue;
    }

    read_meminfo_node(stats, node);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_MEM_TYPE = {
  .st_name = "ST_MEM",
};
