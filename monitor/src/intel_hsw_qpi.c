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

#define MASK0    0x238
#define MASK1    0x23C
#define MATCH0   0x228
#define MATCH1   0x22C

#define CTL_KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", "")

#define CTR_KEYS \
    X(CTR0, "E,W=48,U=flt", ""), \
    X(CTR1, "E,W=48,U=flt", ""), \
    X(CTR2, "E,W=48,U=flt", ""), \
    X(CTR3, "E,W=48,U=flt", "")

#define KEYS CTL_KEYS, CTR_KEYS

#define PERF_EVENT(event, umask)		\
  ( (event)					\
    | (umask << 8)				\
    | (0UL << 18) /* Edge Detection. */		\
    | (1UL << 21) /* Enable extra bit. */	\
    | (1UL << 22) /* Enable. */			\
    | (0UL << 23) /* Invert */			\
  )

#define TxL_FLITS_G1_SNP  PERF_EVENT(0x00,0x01) //!< snoops requests
#define TxL_FLITS_G1_HOM  PERF_EVENT(0x00,0x04) //!< snoop responses
#define G1_DRS_DATA       PERF_EVENT(0x02,0x08) //!< for data bandwidth, flits x 8B/time
#define G2_NCB_DATA       PERF_EVENT(0x03,0x04) //!< for data bandwidth, flits x 8B/time

static int intel_hsw_qpi_begin(struct stats_type *type)
{
  int nr = 0;
  int dids[] = {0x2F32, 0x2F33, 0x2F3A};
  int nr_dids = 3;
  uint32_t events[] = {TxL_FLITS_G1_SNP,  TxL_FLITS_G1_HOM, G1_DRS_DATA, G2_NCB_DATA};
  int nr_events = 4;

  char **dev_paths = NULL;
  int nr_devs;

  if (pci_map_create(&dev_paths, &nr_devs, dids, nr_dids) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    if (intel_snb_uncore_begin_dev(dev_paths[i], events, nr_events) == 0)
      nr++;
  
  if (nr == 0)
    type->st_enabled = 0;
  pci_map_destroy(&dev_paths, nr_devs);
  return nr > 0 ? 0 : -1;

}

static void intel_hsw_qpi_collect(struct stats_type *type)
{
  int dids[] = {0x2F32, 0x2F33, 0x2F3A};
  int nr_dids = 3;

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, nr_dids) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_uncore_collect_dev(type, dev_paths[i]);  
  pci_map_destroy(&dev_paths, nr_devs);
}

struct stats_type intel_hsw_qpi_stats_type = {
  .st_name = "intel_hsw_qpi",
  .st_begin = &intel_hsw_qpi_begin,
  .st_collect = &intel_hsw_qpi_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
