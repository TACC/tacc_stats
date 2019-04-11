#include <stddef.h>
#include <string.h>
#include "stats.h"
#include "collect.h"
#include "trace.h"

// # cat /proc/sys/lnet/stats
// # cat /sys/kernel/debug/lnet/stats -> Lustre Client > 2.6
// 0 1172 0 195805494 204125982 0 16957 216828482753 708781379083 0 3268048
//
// See lustre-1.8.5/lnet/lnet/router_proc.c
// Values are from the_lnet.ln_counters {
//   msgs_alloc, // Number of currently active messages.
//   msgs_max, // Highwater of msgs_alloc.
//   errors, // Unused.
//   send_count, // Messages sent.
//   recv_count, // Messages dropped.
//   route_count, // Only used on routers?
//   drop_count, // Messages dropped, recv size only?
//   send_length, // Bytes sent.
//   recv_length, // Bytes received.
//   route_length, // Bytes of routed messages.  Routers only?
//   drop_length, // Bytes dropped, recv size only?
// }

#define KEYS \
  X(tx_msgs, "E", ""), \
  X(rx_msgs, "E", ""), \
  X(rx_msgs_dropped, "E", ""), \
  X(tx_bytes, "E,U=B", ""), \
  X(rx_bytes, "E,U=B", ""), \
  X(rx_bytes_dropped, "E", "")

static void lnet_collect(struct stats_type *type)
{
  const char *path = "/proc/sys/lnet/stats";
  struct stats *stats = get_current_stats(type, NULL);

  if (stats == NULL)
    return;

  path_collect_key_list(path, stats,
			"msgs_alloc", "msgs_alloc_max", "errors", "tx_msgs",
			"rx_msgs", "route_msgs", "rx_msgs_dropped", "tx_bytes",
			"rx_bytes", "route_bytes", "rx_bytes_dropped",
			NULL);
}

struct stats_type lnet_stats_type = {
  .st_name = "lnet",
  .st_collect = &lnet_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
