#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/if.h>
#include "stats.h"
#include "collect.h"
#include "pscanf.h"
#include "trace.h"

#define KEYS \
  X(collisions, "E", ""), \
  X(multicast, "E", ""), \
  X(rx_bytes, "E,U=B", ""), \
  X(rx_compressed, "E", ""), \
  X(rx_crc_errors, "E", ""), \
  X(rx_dropped, "E", ""), \
  X(rx_errors, "E", ""), \
  X(rx_fifo_errors, "E", ""), \
  X(rx_frame_errors, "E", ""), \
  X(rx_length_errors, "E", ""), \
  X(rx_missed_errors, "E", ""), \
  X(rx_over_errors, "E", ""), \
  X(rx_packets, "E", ""), \
  X(tx_aborted_errors, "E", ""), \
  X(tx_bytes, "E,U=B", ""), \
  X(tx_carrier_errors, "E", ""), \
  X(tx_compressed, "E", ""), \
  X(tx_dropped, "E", ""), \
  X(tx_errors, "E", ""), \
  X(tx_fifo_errors, "E", ""), \
  X(tx_heartbeat_errors, "E", ""), \
  X(tx_packets, "E", ""), \
  X(tx_window_errors, "E", "")

static void net_collect_dev(struct stats_type *type, const char *dev)
{
  struct stats *stats = NULL;
  char path[80];

  stats = get_current_stats(type, dev);
  if (stats == NULL)
    return;

  snprintf(path, sizeof(path), "/sys/class/net/%s/statistics", dev);
  path_collect_key_value_dir(path, stats);
}

static void net_collect(struct stats_type *type)
{
  const char *dir_path = "/sys/class/net";
  DIR *dir = NULL;

  dir = opendir(dir_path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", dir_path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    unsigned int flags;
    char flags_path[80];

    if (ent->d_name[0] == '.')
      continue;

    /* Only collect if dev is up. */
    snprintf(flags_path, sizeof(flags_path), "/sys/class/net/%s/flags", ent->d_name);
    if (pscanf(flags_path, "%x", &flags) != 1) {
      //ERROR("cannot read flags for device `%s'\n", ent->d_name);
      continue;
    }

#define NET_FLAGS \
  X(IFF_UP), \
  X(IFF_BROADCAST), \
  X(IFF_DEBUG), \
  X(IFF_LOOPBACK), \
  X(IFF_POINTOPOINT), \
  X(IFF_NOTRAILERS), \
  X(IFF_RUNNING), \
  X(IFF_NOARP), \
  X(IFF_PROMISC), \
  X(IFF_ALLMULTI), \
  X(IFF_MASTER), \
  X(IFF_SLAVE), \
  X(IFF_MULTICAST), \
  X(IFF_VOLATILE), \
  X(IFF_PORTSEL), \
  X(IFF_AUTOMEDIA), \
  X(IFF_DYNAMIC)

#define X(F) ((flags & F) ? " " #F : "")
    TRACE("dev %s, flags %u%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s\n",
          ent->d_name, flags, NET_FLAGS);
#undef X

    if (flags & IFF_UP)
      net_collect_dev(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type net_stats_type = {
  .st_name = "net",
  .st_collect = &net_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
