#ifndef HOST_MEM_JOB_H_
#define HOST_MEM_JOB_H_

#include "stats.h"

/* Job-scoped cgroup memory (overlap subset of host_mem KEYS + mem_peak).
 * Not NUMA meminfo — see shared-node-affinity-monitor-contract. */
#define KEYS                                                                                       \
  X(mem_used, "U=KB", "cgroup memory.current at job scope"),                                       \
      X(mem_peak, "U=KB", "cgroup memory.peak at job scope"),                                      \
      X(anon_pages, "U=KB", "cgroup memory.stat anon"),                                            \
      X(file_pages, "U=KB", "cgroup memory.stat file"),                                            \
      X(mapped, "U=KB", "cgroup memory.stat file_mapped"),                                         \
      X(dirty, "U=KB", "cgroup memory.stat file_dirty"),                                           \
      X(writeback, "U=KB", "cgroup memory.stat file_writeback"),                                   \
      X(page_tables, "U=KB", "cgroup memory.stat pagetables")

#endif
