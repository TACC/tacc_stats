#define _GNU_SOURCE
#include "stats.h"
#include "trace.h"

void read_key_value(const char *path, struct stats *stats);

void read_vmstat(void)
{
  struct stats *vm_stats = NULL;

  vm_stats = get_current_stats(ST_VM, NULL);
  if (vm_stats == NULL) {
    ERROR("cannot get vm_stats: %m\n");
    return;
  }

  read_key_value("/proc/vmstat", vm_stats);
}
