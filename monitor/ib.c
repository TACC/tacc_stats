#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include "stats.h"
#include "collect.h"
#include "trace.h"

//const char *perfquery = "/opt/ofed/bin/perfquery";

// modified by charngda, for CCR system
const char *perfquery = "/usr/sbin/perfquery";

#define KEYS \
  X(excessive_buffer_overrun_errors, "E", ""), \
  X(link_downed, "E", "failed link error recoveries"), \
  X(link_error_recovery, "E", "successful link error recoveries"), \
  X(local_link_integrity_errors, "E", ""), \
  X(port_rcv_constraint_errors, "E", "packets discarded due to constraint"), \
  X(port_rcv_data, "E,U=4B", "data received"), \
  X(port_rcv_errors, "E", "bad packets received"), \
  X(port_rcv_packets, "E", "packets received"), \
  X(port_rcv_remote_physical_errors, "E", "EBP packets received"), \
  X(port_rcv_switch_relay_errors, "E", ""), \
  X(port_xmit_constraint_errors, "E", "packets not transmitted due to constraint"), \
  X(port_xmit_data, "E,U=4B", "data transmitted"), \
  X(port_xmit_discards, "E", "packets discarded due to down or congested port"), \
  X(port_xmit_packets, "E", "packets transmitted"), \
  X(port_xmit_wait, "E,U=ms", "wait time for credits or arbitration"), \
  X(symbol_error, "E", "minor link errors"), \
  X(VL15_dropped, "E", "")

static void collect_ib_dev(struct stats_type *type, const char *dev)
{
  int port;
  for (port = 1; port <= 2; port++) {
    char path[80], id[80], cmd[160];
    FILE *file = NULL;
    char file_buf[4096];
    unsigned int lid;
    struct stats *stats = NULL;

    snprintf(path, sizeof(path), "/sys/class/infiniband/%s/ports/%i/state", dev, port);
    file = fopen(path, "r");
    if (file == NULL)
      goto next; /* ERROR("cannot open `%s': %m\n", path); */
    setvbuf(file, file_buf, _IOFBF, sizeof(file_buf));

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
    if (file == NULL)
      goto next;
    setvbuf(file, file_buf, _IOFBF, sizeof(file_buf));

    if (fscanf(file, "%x", &lid) != 1)
      goto next;

    fclose(file);
    file = NULL;

    /* Call perfquery to clear stats.  Blech! */
    snprintf(cmd, sizeof(cmd), "%s -R %#x %d", perfquery, lid, port);
    int cmd_rc = system(cmd);
    if (cmd_rc != 0)
      ERROR("`%s' exited with status %d\n", cmd, cmd_rc);

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

struct stats_type ib_stats_type = {
  .st_name = "ib",
  .st_collect = &collect_ib,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
