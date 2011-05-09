#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "stats.h"
#include "trace.h"

// From ipc/shm.c
// # cat /proc/sysvipc/shm
// key      shmid perms       size  cpid  lpid nattch   uid   gid  cuid  cgid      atime      dtime      ctime
//   0     131072   666    1048576  2720  2720      1     0     0     0     0 1304962654          0 1304962654

// "%10d %10d  %4o %10u %5u %5u  %5d %5u %5u %5u %5u %10lu %10lu %10lu\n"
// return seq_printf(s, format,
//                   shp->shm_perm.key,
//                   shp->id,
//                   shp->shm_perm.mode,
//                   shp->shm_segsz,
//                   shp->shm_cprid,
//                   shp->shm_lprid,
//                   is_file_hugepages(shp->shm_file) ? (file_count(shp->shm_file) - 1) : shp->shm_nattch,
//                   shp->shm_perm.uid,
//                   shp->shm_perm.gid,
//                   shp->shm_perm.cuid,
//                   shp->shm_perm.cgid,
//                   shp->shm_atim,
//                   shp->shm_dtim,
//                   shp->shm_ctim);

#define KEYS \
  X(mem_used, "U=B", "System V shared memory used"), \
  X(nr_segs, "", "number of System V shared segments used")

static void collect_sysv_shm(struct stats_type *type)
{
  struct stats *stats = NULL;
  const char *shm_path = "/proc/sysvipc/shm";
  FILE *shm_file = NULL;
  char *line_buf = NULL;
  size_t line_buf_size = 0;

  stats = get_current_stats(type, NULL);
  if (stats == NULL)
    goto out;

  shm_file = fopen(shm_path, "r");
  if (shm_file == NULL) {
    ERROR("cannot open `%s': %m\n", shm_path);
    goto out;
  }

  /* Skip header. */
  getline(&line_buf, &line_buf_size, shm_file);

  unsigned long long mem_used = 0, nr_segs = 0;

  while (getline(&line_buf, &line_buf_size, shm_file) >= 0) {
    unsigned long long seg_size = 0;
    if (sscanf(line_buf, "%*d %*d %*o %llu", &seg_size) < 0)
      continue;

    mem_used += seg_size;
    nr_segs++;
  }

  stats_set(stats, "mem_used", mem_used);
  stats_set(stats, "nr_segs", nr_segs);

 out:
  free(line_buf);
  if (shm_file != NULL)
    fclose(shm_file);
}

struct stats_type STATS_TYPE_SYSV_SHM = {
  .st_name = "sysv_shm",
  .st_collect = &collect_sysv_shm,
#define X(k,o,d,r...) #k "," o
  .st_schema_def = JOIN(KEYS),
#undef X
};
