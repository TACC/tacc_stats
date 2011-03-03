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

static void collect_diskstats(struct stats_type *type)
{
  const char *path = "/proc/diskstats";
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  /* /proc/diskstats fields:
     major minor name rd_reqs rd_merges rd_sectors rd_ms
                      wr_reqs wr_merges wr_sectors wr_ms
                      cur_reqs io_ms io_avg_ms */
  /* We ignore major and minor. */

#define BLOCK_KEYS \
  X(rd_reqs), X(rd_merges), X(rd_sectors), X(rd_ms), \
  X(wr_reqs), X(wr_merges), X(wr_sectors), X(wr_ms), \
  X(cur_reqs), X(io_ms), X(io_avg_ms)

  while (getline(&line, &line_size, file) >= 0) {
    char dev[32];
#define X(K) K
    unsigned long long BLOCK_KEYS;
#undef X

#define X(K) &K
    if (sscanf(line, "%*u %*u %31s "
               "%llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
               dev, BLOCK_KEYS) != 12)
      continue;
#undef X

    struct stats *stats = get_current_stats(type, dev);
    if (stats == NULL)
      continue;

#define X(K) stats_set(stats, #K, K)
    BLOCK_KEYS;
#undef X
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);
}

struct stats_type ST_BLOCK_TYPE = {
  .st_name = "ST_BLOCK",
  .st_collect = (void (*[])()) { &collect_diskstats, NULL, },
  .st_schema = (char *[]) {
#define X(K) #K
    BLOCK_KEYS, NULL,
#undef X
  },
};
