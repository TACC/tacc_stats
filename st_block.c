#include <stddef.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "collect.h"
#include "trace.h"

/* Need to account for units.  According to block/stat.txt, in
   /sys/block/DEV/stat sector means 512B (as opposed to real sector
   size of device). */
/* All X_ticks members and time_in_queue are in ms. */

#define BLOCK_KEYS \
  X(rd_ios, "event", "read requests processed"), \
  X(rd_merges, "event", "read requests merged with in-queue requests"), \
  X(rd_sectors, "event,unit=512B", "sectors read"), \
  X(rd_ticks, "event,unit=ms", "wait time for read requests"), \
  X(wr_ios, "event", "write requests processed"), \
  X(wr_merges, "event", "write requests merged with in-queue requests"), \
  X(wr_sectors, "event,unit=512B", "sectors written"), \
  X(wr_ticks, "event,unit=ms", "wait time for write requests"), \
  X(in_flight, "requests in flight"), \
  X(io_ticks, "event,unit=ms", "time active"), \
  X(time_in_queue, "event,unit=ms", "wait time for all requests")

static void collect_block_dev(struct stats_type *type, const char *dev)
{
  struct stats *stats = get_current_stats(type, dev);
  if (stats == NULL)
    return;

  char path[80];
  snprintf(path, sizeof(path), "/sys/block/%s/stat", dev);

#define X(k,r...) #k
  collect_key_list(stats, path, BLOCK_KEYS, NULL);
#undef X
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
  .st_name = "block",
  .st_collect = &collect_block,
#define X(k,r...) #k
  .st_schema = (char *[]) { BLOCK_KEYS, NULL, },
#undef X
};
