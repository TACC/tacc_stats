#define _GNU_SOURCE
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include "stats.h"
#include "trace.h"

static void collect_net_dev(struct stats_type *type)
{
  const char *path = "/proc/net/dev";
  FILE *file = NULL;
  char *line = NULL;
  size_t line_size = 0;

  file = fopen(path, "r");
  if (file == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  /* It's just horrible. (Lots of space taken out.) */
  // $ cat /proc/net/dev
  // Inter-|   Receive                                             |  Transmit
  //  face |bytes packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  //     lo:206258552443 1056240623 0 0 0 0 0 0 206258552443 1056240623 0 0 0 0 0 0
  // ...

#define NET_DEV_KEYS \
  X(rx_bytes), X(rx_packets), X(rx_errors), X(rx_drop), X(rx_fifo), X(rx_frame), X(rx_compressed), X(rx_multicast), \
  X(tx_bytes), X(tx_packets), X(tx_errors), X(tx_drop), X(tx_fifo), X(tx_collisions), X(tx_carrier), X(tx_compressed)

  /* Burn first two lines. */
  getline(&line, &line_size, file);
  getline(&line, &line_size, file);

  while (getline(&line, &line_size, file) >= 0) {
    char *iface, *rest = line;
    iface = strsep(&rest, ":");
    while (*iface == ' ')
      iface++;
    if (*iface == 0 || rest == NULL)
      continue;

#define X(K) K
    unsigned long long NET_DEV_KEYS;
#undef X

#define X(K) &K
    if (sscanf(rest,
               "%llu %llu %llu %llu %llu %llu %llu %llu"
               "%llu %llu %llu %llu %llu %llu %llu %llu",
               NET_DEV_KEYS) != 16)
      continue;
#undef X

    struct stats *stats = get_current_stats(type, iface);
    if (stats == NULL) {
      ERROR("cannot get net dev stats: %m\n");
      continue;
    }

#define X(K) stats_set(stats, #K, K)
    NET_DEV_KEYS;
#undef X
  }

 out:
  free(line);
  if (file != NULL)
    fclose(file);
}

struct stats_type ST_NET_TYPE = {
  .st_name = "ST_NET",
  .st_collect = (void (*[])()) { &collect_net_dev, NULL, },
  .st_schema = (char *[]) {
#define X(K) #K
    NET_DEV_KEYS, NULL,
#undef X
  },
};
