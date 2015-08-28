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
  X(CTL0, "C", ""),   \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", "")

#define CTR_KEYS	   \
    X(CTR0, "E,W=48", ""), \
      X(CTR1, "E,W=48", ""),			\
      X(CTR2, "E,W=48", ""),			\
      X(CTR3, "E,W=48", ""),			\
      X(FIXED_CTR,"E,W=48","")

#define KEYS CTL_KEYS, CTR_KEYS

#define PERF_EVENT(event, umask)		\
  ( (event)					\
    | (umask << 8)				\
    | (0UL << 17) /* reset counter */		\
    | (0UL << 18) /* Edge Detection. */		\
    | (1UL << 22) /* Enable. */			\
    | (0UL << 23) /* Invert */			\
    | (0x01UL << 24) /* Threshold */		\
    )

#define CAS_READS           PERF_EVENT(0x04, 0x03)
#define CAS_WRITES          PERF_EVENT(0x04, 0x0C)
#define ACT_COUNT           PERF_EVENT(0x01, 0x00)
#define PRE_COUNT_ALL       PERF_EVENT(0x02, 0x03)
#define PRE_COUNT_MISS      PERF_EVENT(0x02, 0x01)

static int intel_snb_imc_begin_dev(char *bus_dev, uint32_t *events, 
				   size_t nr_events)
{
  int rc = -1;
  char pci_path[80];
  int pci_fd = -1;
  uint32_t ctl;

  snprintf(pci_path, sizeof(pci_path), "%s/%s", "/proc/bus/pci", bus_dev);

  pci_fd = open(pci_path, O_RDWR);
  if (pci_fd < 0) {
    ERROR("cannot open `%s': %m\n", pci_path);
    goto out;
  }

  ctl = 0x10100UL; // enable freeze (bit 16), freeze (bit 8)
  if (pwrite(pci_fd, &ctl, sizeof(ctl), BOX_CTL) < 0) {
    ERROR("cannot enable freeze of MC counters: %m\n");
    goto out;
  }
  
  ctl = 0x80000UL; // Reset Fixed Counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), IMC_FIXED_CTL) < 0) {
    ERROR("cannot undo reset of MC Fixed counter: %m\n");
    goto out;
  }
 
  /* Select Events for MC counters, CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  /* Manually reset programmable MC counters. They are 4 apart, 
     but each counter register is split into 2 32-bit registers, A and B */
  uint32_t zero = 0x0UL;
  for (i = 0; i < nr_events; i++) {
    if (pwrite(pci_fd, &zero, sizeof(zero), A_CTR0 + 8*i) < 0 || 
	pwrite(pci_fd, &zero, sizeof(zero), B_CTR0 + 8*i) < 0) { 
      ERROR("cannot reset counter %08X,%08X through `%s': %m\n", 
	    (unsigned) A_CTR0 + 8*i, (unsigned) B_CTR0 + 8*i,
            pci_path);
      goto out;
    }
  }

  ctl = 0x400000UL; // Enable Fixed Counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), IMC_FIXED_CTL) < 0) {
    ERROR("cannot undo reset of MC Fixed counter: %m\n");
    goto out;
  }
  
  ctl = 0x10000UL; // unfreeze counters
  if (pwrite(pci_fd, &ctl, sizeof(ctl), BOX_CTL) < 0) {
    ERROR("cannot unfreeze MC counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_snb_imc_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t events[] = {
    CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,
  };
  int dids[] = {0x3cb0, 0x3cb1, 0x3cb4, 0x3cb5}; 
  
  char **dev_paths = NULL;
  int nr_devs;

  if (pci_map_create(&dev_paths, &nr_devs, dids, 4) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    if (intel_snb_imc_begin_dev(dev_paths[i], events, 4) == 0)
      nr++;

  if (nr == 0)
    type->st_enabled = 0;

  return nr > 0 ? 0 : -1;
}

static void intel_snb_imc_collect(struct stats_type *type)
{
  int dids[] = {0x3cb0, 0x3cb1, 0x3cb4, 0x3cb5}; 

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, 4) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_uncore_collect_dev(type, dev_paths[i]);  
}

struct stats_type intel_snb_imc_stats_type = {
  .st_name = "intel_snb_imc",
  .st_begin = &intel_snb_imc_begin,
  .st_collect = &intel_snb_imc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
