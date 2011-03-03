#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "collect.h"
#include "trace.h"

/* Fields for mlx4, mthca: */

#define IB_KEYS \
  X(excessive_buffer_overrun_errors), \
  X(link_downed), \
  X(link_error_recovery), \
  X(local_link_integrity_errors), \
  X(port_rcv_constraint_errors), \
  X(port_rcv_data), \
  X(port_rcv_errors), \
  X(port_rcv_packets), \
  X(port_rcv_remote_physical_errors), \
  X(port_rcv_switch_relay_errors), \
  X(port_xmit_constraint_errors), \
  X(port_xmit_data), \
  X(port_xmit_discards), \
  X(port_xmit_packets), \
  X(port_xmit_wait), \
  X(symbol_error), \
  X(VL15_dropped)

static void collect_ib_dev(struct stats_type *type, const char *dev)
{
  int port;
  for (port = 1; port <= 2; port++) {
    char path[80], id[80], cmd[160];
    FILE *file = NULL;
    unsigned int lid;
    struct stats *stats = NULL;

    snprintf(path, sizeof(path), "/sys/class/infiniband/%s/ports/%i/state", dev, port);
    file = fopen(path, "r");
    if (file == NULL)
      goto next; /* ERROR("cannot open `%s': %m\n", path); */

    char buf[80] = { 0 };
    if (fgets(buf, sizeof(buf), file) == NULL)
      goto next;

    fclose(file);
    file = NULL;

    if (strstr(buf, "ACTIVE") == NULL)
      goto next;

    TRACE("dev %s, port %i\n", dev, port);

    snprintf(id, sizeof(id), "%s.%i", dev, port); /* XXX */
    stats = get_current_stats(type, id);
    if (stats == NULL)
      goto next;

    snprintf(path, sizeof(path), "/sys/class/infiniband/%s/ports/%i/counters", dev, port);
    collect_key_value_dir(stats, path);

    /* Get the LID for perfquery. */
    snprintf(path, sizeof(path), "/sys/class/infiniband/%s/ports/%i/lid", dev, port);
    file = fopen(path, "r");
    if (fscanf(file, "%x", &lid) != 1)
      goto next;

    fclose(file);
    file = NULL;

    /* Call perfquery to clear stats.  Blech! */
    snprintf(cmd, sizeof(cmd), "/opt/ofed/sbin/perfquery -R %#x %d", lid, port);
    TRACE("system `%s'\n", cmd);
    system(cmd);

  next:
    if (file != NULL)
      fclose(file);
    file = NULL;
  }
}

static void collect_ib(struct stats_type *type)
{
  const char *path = "/sys/class/infiniband";
  DIR *dir = NULL;

  dir = opendir(path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (ent->d_name[0] == '.')
      continue;
    collect_ib_dev(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_IB_TYPE = {
  .st_name = "ST_IB",
  .st_collect = (void (*[])()) { &collect_ib, NULL, },
#define X(K) #K
  .st_schema = (char *[]) { IB_KEYS, NULL, },
#undef X
};
