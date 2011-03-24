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
#include "trace.h"

#define KEYS \
  X(collisions, "event", ""), \
  X(multicast, "event", ""), \
  X(rx_bytes, "event,unit=B", ""), \
  X(rx_compressed, "event", ""), \
  X(rx_crc_errors, "event", ""), \
  X(rx_dropped, "event", ""), \
  X(rx_errors, "event", ""), \
  X(rx_fifo_errors, "event", ""), \
  X(rx_frame_errors, "event", ""), \
  X(rx_length_errors, "event", ""), \
  X(rx_missed_errors, "event", ""), \
  X(rx_over_errors, "event", ""), \
  X(rx_packets, "event", ""), \
  X(tx_aborted_errors, "event", ""), \
  X(tx_bytes, "event,unit=B", ""), \
  X(tx_carrier_errors, "event", ""), \
  X(tx_compressed, "event", ""), \
  X(tx_dropped, "event", ""), \
  X(tx_errors, "event", ""), \
  X(tx_fifo_errors, "event", ""), \
  X(tx_heartbeat_errors, "event", ""), \
  X(tx_packets, "event", ""), \
  X(tx_window_errors, "event", "")

static void collect_net_dev(struct stats_type *type, const char *dev)
{
  struct stats *stats = NULL;
  char path[80];

  stats = get_current_stats(type, dev);
  if (stats == NULL)
    return;

  snprintf(path, sizeof(path), "/sys/class/net/%s/statistics", dev);
  collect_key_value_dir(stats, path);
}

static void collect_net(struct stats_type *type)
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
    FILE *flags_file = NULL;

    if (ent->d_name[0] == '.')
      goto next;

    /* Only collect if dev is up. */
    snprintf(flags_path, sizeof(flags_path), "/sys/class/net/%s/flags", ent->d_name);
    flags_file = fopen(flags_path, "r");
    if (flags_file == NULL) {
      ERROR("cannot open `%s'; %m\n", flags_path);
      goto next;
    }

    if (fscanf(flags_file, "%x", &flags) != 1) {
      ERROR("cannot read flags for device `%s'\n", ent->d_name);
      goto next;
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

    if ((flags & IFF_UP) == 0)
      goto next;

    collect_net_dev(type, ent->d_name);

  next:
    if (flags_file != NULL)
      fclose(flags_file);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type STATS_TYPE_NET = {
  .st_name = "net",
  .st_collect = &collect_net,
#define X(k,r...) #k
  .st_schema = (char *[]) { KEYS, NULL, },
#undef X
};
