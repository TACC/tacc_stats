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
    X(CTR0, "E,W=44", ""), \
    X(CTR1, "E,W=44", ""), \
    X(CTR2, "E,W=44", ""), \
    X(CTR3, "E,W=44", "")

#define KEYS CTL_KEYS, CTR_KEYS

#define PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 17) /* reset counter */ \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  | (0x01UL << 24) /* Threshold */ \
  )

#define TxR_INSERTS      PERF_EVENT(0x24,0x04)  //!< CTR0 only
#define CLOCKTICKS       PERF_EVENT(0x01,0x00)
#define RING_AD_USED_ALL PERF_EVENT(0x07,0x0F)
#define RING_AK_USED_ALL PERF_EVENT(0x08,0x0F) 
#define RING_BL_USED_ALL PERF_EVENT(0x09,0x0F) 

static int intel_snb_r2pci_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t events[] = {
    TxR_INSERTS, RING_BL_USED_ALL, RING_AD_USED_ALL, RING_AK_USED_ALL,
  };

  int dids[] = {0x3c43};

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

static void intel_snb_r2pci_collect(struct stats_type *type)
{
  int dids[] = {0x3c43};

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, 1) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_uncore_collect_dev(type, dev_paths[i]);  
  pci_map_destroy(&dev_paths, nr_devs);
}

struct stats_type intel_snb_r2pci_stats_type = {
  .st_name = "intel_snb_r2pci",
  .st_begin = &intel_snb_r2pci_begin,
  .st_collect = &intel_snb_r2pci_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
