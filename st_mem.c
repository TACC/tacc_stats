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

/* TODO Move numastat to its own file, or remove completely. */

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

/* On 2.6.18-194.32.1 files in /dev/shm show up as FilePages in
   nodeN/meminfo and as Cached in /proc/meminfo. */

/* Dirty, Writeback, AnonPages, Mapped, Slab, PageTables,
   NFS_Unstable, Bounce. */

#define KEYS \
  X(MemTotal, "unit=KB", ""), \
  X(MemFree, "unit=KB", ""), \
  X(MemUsed, "unit=KB", ""), \
  X(Active, "unit=KB", ""), \
  X(Inactive, "unit=KB", ""), \
  X(HighTotal, "unit=KB", ""), \
  X(HighFree, "unit=KB", ""), \
  X(LowTotal, "unit=KB", ""), \
  X(LowFree, "unit=KB", ""), \
  X(Dirty, "unit=KB", ""), \
  X(Writeback, "unit=KB", ""), \
  X(FilePages, "unit=KB", ""), \
  X(Mapped, "unit=KB", ""), \
  X(AnonPages, "unit=KB", ""), \
  X(PageTables, "unit=KB", ""), \
  X(NFS_Unstable, "unit=KB", ""), \
  X(Bounce, "unit=KB", ""), \
  X(Slab, "unit=KB", ""), \
  X(HugePages_Total, "", ""), \
  X(HugePages_Free, "", ""), \
  X(numa_hit, "event", ""), \
  X(numa_miss, "event", ""), \
  X(numa_foreign, "event", ""), \
  X(interleave_hit, "event", ""), \
  X(local_node, "event", ""), \
  X(other_node, "event", "")

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
    char key[81];
    unsigned long long val = 0;

    key[0] = 0;
    if (sscanf(line, "Node %*d %80[^:]: %llu %*s", key, &val) < 2)
      continue;

    if (key[0] == 0)
      continue;

    stats_set(stats, key, val);
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

struct stats_type STATS_TYPE_MEM = {
  .st_name = "mem",
  .st_collect = &collect_mem,
#define X(k,o,d,r...) #k "," o ",desc=" d "; "
  .st_schema_def = STRJOIN(KEYS),
#undef X
};
