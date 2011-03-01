#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stats.h"
#include "trace.h"

struct stats_type ST_IB_TYPE = {
  .st_name = "ST_IB",
};

const char *ib_stats_cmd = "/opt/ofed/sbin/perfquery -r";

// $ perfquery
// # Port counters: Lid 936 port 1
// PortSelect:......................1
// CounterSelect:...................0x0000
// SymbolErrors:....................0
// LinkRecovers:....................0
// LinkDowned:......................0
// RcvErrors:.......................0
// RcvRemotePhysErrors:.............0
// RcvSwRelayErrors:................0
// XmtDiscards:.....................0
// XmtConstraintErrors:.............0
// RcvConstraintErrors:.............0
// LinkIntegrityErrors:.............0
// ExcBufOverrunErrors:.............0
// VL15Dropped:.....................0
// XmtData:.........................905972985
// RcvData:.........................2411533950
// XmtPkts:.........................22945597
// RcvPkts:.........................26264095

void read_ib_stats(void)
{
  struct stats *ib_stats = NULL;
  FILE *pipe = NULL;
  char *line = NULL;
  size_t line_size = 0;

  pipe = popen(ib_stats_cmd, "r");
  if (pipe == NULL) {
    ERROR("cannot execute `%s': %m\n", ib_stats_cmd);
    goto out;
  }

  ib_stats = get_current_stats(ST_IB, NULL);
  if (ib_stats == NULL) {
    ERROR("cannot get ib_stats: %m\n");
    goto out;
  }

  while (getline(&line, &line_size, pipe) >= 0) {
    char *key, *rest = line;
    unsigned long long val;

    key = strsep(&rest, ":");
    if (*key == 0 || rest == NULL)
      continue;

    while (*rest == '.')
      rest++;

    errno = 0;
    val = strtoull(rest, NULL, 0);
    if (errno != 0)
      continue;

    /* Data vaules are counted in units of 4 octets. */
    if (strcmp(key, "XmtData") == 0 || strcmp(key, "RcvData") == 0)
      val *= 4;

    stats_set(ib_stats, key, val);
  }

 out:
  free(line);
  if (pipe != NULL)
    pclose(pipe);
}
