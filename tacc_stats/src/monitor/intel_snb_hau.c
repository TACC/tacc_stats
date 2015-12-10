#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>
#include <malloc.h>
#include <ctype.h>
#include <fcntl.h>
#include "stats.h"
#include "trace.h"
#include "pscanf.h"
#include "pci.h"
#include "intel_snb_uncore.h"

#define CTL_KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", "")

#define CTR_KEYS \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", "")

#define KEYS CTL_KEYS, CTR_KEYS

#define PERF_EVENT(event, umask)		\
  ( (event)					\
    | (umask << 8)				\
    | (0UL << 18)				\
    | (1UL << 22)				\
    | (0UL << 23)				\
    | (0x01UL << 24)				\
    )

#define REQUESTS_READS  PERF_EVENT(0x01,0x03)
#define REQUESTS_WRITES PERF_EVENT(0x01,0x0C)
#define CLOCKTICKS      PERF_EVENT(0x00,0x00)
#define IMC_WRITES      PERF_EVENT(0x1A,0x0F) 

static int intel_snb_hau_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t events[] = {
    REQUESTS_READS, REQUESTS_WRITES, CLOCKTICKS, IMC_WRITES,
  };
  int dids[] = {0x3c46};
  
  char **dev_paths = NULL;
  int nr_devs;
  
  if (pci_map_create(&dev_paths, &nr_devs, dids, 1) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    if (intel_snb_uncore_begin_dev(dev_paths[i], events, 4) == 0)
      nr++;   
  
  if (nr == 0)
    type->st_enabled = 0;

  pci_map_destroy(&dev_paths, nr_devs);
  return nr > 0 ? 0 : -1;
}


static void intel_snb_hau_collect(struct stats_type *type)
{
  int dids[] = {0x3c46};

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, 1) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_uncore_collect_dev(type, dev_paths[i]);  
  pci_map_destroy(&dev_paths, nr_devs);
}

struct stats_type intel_snb_hau_stats_type = {
  .st_name = "intel_snb_hau",
  .st_begin = &intel_snb_hau_begin,
  .st_collect = &intel_snb_hau_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
