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

/* Need to account for units.  According to block/stat.txt, in
/sys/block/DEV/stat sector means 512B (as opposed to real sector size
of device). */

static void collect_block_dev(struct stats_type *type, const char *dev)
{
  char path[80];
  FILE *file = NULL;

  snprintf(path, sizeof(path), "/sys/block/%s/stat", dev);
  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

#define BLOCK_KEYS \
  X(rd_reqs), X(rd_merges), X(rd_sectors), X(rd_ms), \
  X(wr_reqs), X(wr_merges), X(wr_sectors), X(wr_ms), \
  X(cur_reqs), X(io_ms), X(io_avg_ms)

#define X(K) K
  unsigned long long BLOCK_KEYS;
#undef X

#define X(K) &K
  if (fscanf(file, "%llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
             BLOCK_KEYS) != 11)
    goto out;
#undef X

  struct stats *stats = get_current_stats(type, dev);
  if (stats == NULL)
    goto out;

#define X(K) stats_set(stats, #K, K)
  BLOCK_KEYS;
#undef X

 out:
  if (file != NULL)
    fclose(file);
}

static void collect_block(struct stats_type *type)
{
  const char *path = "/sys/block";
  DIR *dir = NULL;

  dir = opendir(path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (ent->d_name[0] == '.')
      continue;
    /* Ignore ram*.  FIXME Make this a config. */
    if (strncmp(ent->d_name, "ram", 3) == 0)
      continue;
    collect_block_dev(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_BLOCK_TYPE = {
  .st_name = "ST_BLOCK",
  .st_collect = &collect_block,
  .st_schema = (char *[]) {
#define X(K) #K
    BLOCK_KEYS, NULL,
#undef X
  },
};
