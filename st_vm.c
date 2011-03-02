#define _GNU_SOURCE
#include "stats.h"
#include "trace.h"

void collect_key_value_file(struct stats *stats, const char *path);

static void collect_vmstat(struct stats_type *type)
{
  struct stats *vm_stats = NULL;

  vm_stats = get_current_stats(type, NULL);
  if (vm_stats == NULL) {
    ERROR("cannot get vm_stats: %m\n");
    return;
  }

  collect_key_value_file(vm_stats, "/proc/vmstat");
}

// $ cat /proc/vmstat
// nr_anon_pages 398141
// nr_mapped 12214
// nr_file_pages 3249310
// nr_slab 375643
// nr_page_table_pages 2179
// nr_dirty 3151
// nr_writeback 0
// nr_unstable 0
// nr_bounce 0
// numa_hit 36413908498
// numa_miss 3209704118
// numa_foreign 3209704118
// numa_interleave 331840104
// numa_local 36139492324
// numa_other 3484120292
// pgpgin 1922515
// pgpgout 2940284
// pswpin 0
// pswpout 0
// pgalloc_dma 9
// pgalloc_dma32 0
// pgalloc_normal 39883380286
// pgalloc_high 0
// pgfree 39887512458
// pgactivate 1128012194
// pgdeactivate 141636621
// pgfault 36151347697
// pgmajfault 484632179
// pgrefill_dma 0
// pgrefill_dma32 0
// pgrefill_normal 730475864
// pgrefill_high 0
// pgsteal_dma 0
// pgsteal_dma32 0
// pgsteal_normal 0
// pgsteal_high 0
// pgscan_kswapd_dma 0
// pgscan_kswapd_dma32 0
// pgscan_kswapd_normal 226888136
// pgscan_kswapd_high 0
// pgscan_direct_dma 0
// pgscan_direct_dma32 0
// pgscan_direct_normal 10239904
// pgscan_direct_high 0
// pginodesteal 2218796
// slabs_scanned 3396736
// kswapd_steal 205289183
// kswapd_inodesteal 43649865
// pageoutrun 1288237
// allocstall 18265
// pgrotated 18

struct stats_type ST_VM_TYPE = {
  .st_name = "ST_VM",
  .st_collect = (void (*[])()) { &collect_vmstat, NULL, },
  .st_schema = (char *[]) { NULL, },
};
