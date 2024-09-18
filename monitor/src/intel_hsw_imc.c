/*! 
 \file intel_hsw_imc.c
*/
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
#include "intel_pmc_uncore.h"

//@}

/*! \name KEYS will define the raw schema for this type. 
  
  The required order of registers is:
  -# Control registers in order
  -# Counter registers in order
  -# Fixed counter register
  @{
*/
#define CTL_KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", "")

#define CTR_KEYS \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", ""), \
    X(FIXED_CTR,"E,W=48","")

#define KEYS CTL_KEYS, CTR_KEYS
//@}


/*! \brief Event select
  
  Events are listed in Table 2-61.  They are defined in detail
  in Section 2.5.8.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_hsw_imc_begin()
*/
#define MBOX_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 18) \
  | (1UL << 22) \
  | (0UL << 23) \
  | (0x01UL << 24) \
  )

/*! \name Events

  Events are listed in Table 2-61.  They are defined in detail
  in Section 2.5.8.

@{
 */
#define CAS_READS           MBOX_PERF_EVENT(0x04, 0x03)
#define CAS_WRITES          MBOX_PERF_EVENT(0x04, 0x0C)
#define ACT_COUNT           MBOX_PERF_EVENT(0x01, 0x0B)
#define PRE_COUNT_ALL       MBOX_PERF_EVENT(0x02, 0x03)
#define PRE_COUNT_MISS      MBOX_PERF_EVENT(0x02, 0x01)
//@}

static uint32_t events[] = {
  CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,
};

static int dids[] = {0x2fb0, 0x2fb1, 0x2fb4, 0x2fb5, 
		     0x2fd0, 0x2fd1, 0x2fd4, 0x2fd5}; 

static int intel_hsw_imc_begin(struct stats_type *type)
{
  int nr = 0;

  char **dev_paths = NULL;
  int nr_devs;

  if (pci_map_create(&dev_paths, &nr_devs, dids, 8) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    if (intel_pmc_uncore_begin_dev(dev_paths[i], events, 4) == 0)
      nr++;

  if (nr == 0)
    type->st_enabled = 0;
  pci_map_destroy(&dev_paths, nr_devs);
  return nr > 0 ? 0 : -1;
}

static void intel_hsw_imc_collect(struct stats_type *type)
{
  char **dev_paths = NULL;
  int nr_devs;

  if (pci_map_create(&dev_paths, &nr_devs, dids, 8) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_pmc_uncore_collect_dev(type, dev_paths[i]);  
  pci_map_destroy(&dev_paths, nr_devs);
}

struct stats_type intel_hsw_imc_stats_type = {
  .st_name = "intel_hsw_imc",
  .st_begin = &intel_hsw_imc_begin,
  .st_collect = &intel_hsw_imc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
