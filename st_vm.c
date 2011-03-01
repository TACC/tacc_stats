#define _GNU_SOURCE
#include "stats.h"
#include "trace.h"

void read_key_value(const char *path, struct stats *stats);

static void read_vmstat(struct stats_type *type)
{
  struct stats *vm_stats = NULL;

  vm_stats = get_current_stats(type, NULL);
  if (vm_stats == NULL) {
    ERROR("cannot get vm_stats: %m\n");
    return;
  }

  read_key_value("/proc/vmstat", vm_stats);
}

struct stats_type ST_VM_TYPE = {
  .st_name = "ST_VM",
};
