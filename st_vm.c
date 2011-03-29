#include <stddef.h>
#include "stats.h"
#include "trace.h"
#include "collect.h"

/* TODO Trim this down. */

#define KEYS \
  X(pgpgin, "event", ""), \
  X(pgpgout, "event", ""), \
  X(pswpin, "event", ""), \
  X(pswpout, "event", ""), \
  X(pgalloc_high, "event", ""), \
  X(pgalloc_normal, "event", ""), \
  X(pgalloc_dma, "event", ""), \
  X(pgfree, "event", ""), \
  X(pgactivate, "event", ""), \
  X(pgdeactivate, "event", ""), \
  X(pgfault, "event", ""), \
  X(pgmajfault, "event", ""), \
  X(pgrefill_high, "event", ""), \
  X(pgrefill_normal, "event", ""), \
  X(pgrefill_dma, "event", ""), \
  X(pgsteal_high, "event", ""), \
  X(pgsteal_normal, "event", ""), \
  X(pgsteal_dma, "event", ""), \
  X(pgscan_kswapd_high, "event", ""), \
  X(pgscan_kswapd_normal, "event", ""), \
  X(pgscan_kswapd_dma, "event", ""), \
  X(pgscan_direct_high, "event", ""), \
  X(pgscan_direct_normal, "event", ""), \
  X(pgscan_direct_dma, "event", ""), \
  X(pginodesteal, "event", ""), \
  X(slabs_scanned, "event", ""), \
  X(kswapd_steal, "event", ""), \
  X(kswapd_inodesteal, "event", ""), \
  X(pageoutrun, "event", ""), \
  X(allocstall, "event", ""), \
  X(pgrotated, "event", "")

static void collect_vm(struct stats_type *type)
{
  struct stats *stats = NULL;

  stats = get_current_stats(type, NULL);
  if (stats == NULL)
    return;

  collect_key_value_file(stats, "/proc/vmstat");
}

struct stats_type STATS_TYPE_VM = {
  .st_name = "vm",
  .st_collect = &collect_vm,
#define X(k,o,d,r...) #k "," o ",desc=" d "; "
  .st_schema_def = STRJOIN(KEYS),
#undef X
};
