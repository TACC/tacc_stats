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
#include "collect.h"
#include "trace.h"

/* TODO Units. */

// i182-101# cat /sys/devices/system/node/node0/meminfo
//
// Node 0 MemTotal:      8220940 kB
// Node 0 MemFree:       4559756 kB
// Node 0 MemUsed:       3661184 kB
// Node 0 Active:        2220752 kB
// Node 0 Inactive:       859880 kB
// Node 0 HighTotal:           0 kB
// Node 0 HighFree:            0 kB
// Node 0 LowTotal:      8220940 kB
// Node 0 LowFree:       4559756 kB
// Node 0 Dirty:               4 kB
// Node 0 Writeback:           0 kB
// Node 0 FilePages:     2673328 kB
// Node 0 Mapped:          28296 kB
// Node 0 AnonPages:      406964 kB
// Node 0 PageTables:       2596 kB
// Node 0 NFS_Unstable:        0 kB
// Node 0 Bounce:              0 kB
// Node 0 Slab:           294400 kB
// Node 0 HugePages_Total:     0
// Node 0 HugePages_Free:      0

// # cat /sys/devices/system/node/node0/numastat
// numa_hit 24972369
// numa_miss 41182663
// numa_foreign 12112910
// interleave_hit 49948
// local_node 24910136
// other_node 41244896

#define MEM_KEYS \
  X(MemTotal), \
  X(MemFree), \
  X(MemUsed), \
  X(Active), \
  X(Inactive), \
  X(HighTotal), \
  X(HighFree), \
  X(LowTotal), \
  X(LowFree), \
  X(Dirty), \
  X(Writeback), \
  X(FilePages), \
  X(Mapped), \
  X(AnonPages), \
  X(PageTables), \
  X(NFS_Unstable), \
  X(Bounce), \
  X(Slab), \
  X(HugePages_Total), \
  X(HugePages_Free), \
  X(numa_hit), \
  X(numa_miss), \
  X(numa_foreign), \
  X(interleave_hit), \
  X(local_node), \
  X(other_node)

static void collect_meminfo_node(struct stats *stats, const char *node)
{
  char path[80];
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  snprintf(path, sizeof(path), "/sys/devices/system/node/node%s/meminfo", node);
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
}

static void collect_numastat_node(struct stats *stats, const char *node)
{
  char path[80];

  snprintf(path, sizeof(path), "/sys/devices/system/node/node%s/numastat", node);
  collect_key_value_file(stats, path);
}

static void collect_mem(struct stats_type *type)
{
  const char *dir_path = "/sys/devices/system/node";
  DIR *dir = NULL;

  dir = opendir(dir_path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", dir_path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    struct stats *stats = NULL;
    const char *node;

    if (strncmp(ent->d_name, "node", 4) != 0)
      continue;

    node = ent->d_name + 4;
    stats = get_current_stats(type, node);
    if (stats == NULL)
      continue;

    collect_meminfo_node(stats, node);
    collect_numastat_node(stats, node);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_MEM_TYPE = {
  .st_name = "ST_MEM",
  .st_collect = (void (*[])()) { &collect_mem, NULL, },
#define X(K) #K
  .st_schema = (char *[]) { MEM_KEYS, NULL, },
#undef X
};
