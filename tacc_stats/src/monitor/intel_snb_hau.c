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
#include "check_pci_id.h"
#include "pci_busid_map.h"

/*! \name HAU Global Control Register */
#define HAU_BOX_CTL        0xF4

/*! \name HAU Configurable Performance Monitoring Registers */
#define HAU_CTL0           0xD8
#define HAU_CTL1           0xDC
#define HAU_CTL2           0xE0
#define HAU_CTL3           0xE4

#define HAU_B_CTR0         0xA0
#define HAU_A_CTR0         0xA4
#define HAU_B_CTR1         0xA8
#define HAU_A_CTR1         0xAC
#define HAU_B_CTR2         0xB0
#define HAU_A_CTR2         0xB4
#define HAU_B_CTR3         0xB8
#define HAU_A_CTR3         0xBC

#define HAU_ADRRMATCH0     0x40
#define HAU_ADDRMATCH1     0x44
#define HAU_OPCODEMATCH    0x48

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

#define REQUESTS_READS  HAU_PERF_EVENT(0x01,0x03)
#define REQUESTS_WRITES HAU_PERF_EVENT(0x01,0x0C)
#define CLOCKTICKS      HAU_PERF_EVENT(0x00,0x00)
#define IMC_WRITES      HAU_PERF_EVENT(0x1A,0x0F) 

static int intel_snb_hau_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
{
  int rc = -1;
  char pci_path[80];
  int pci_fd = -1;
  uint32_t ctl;

  snprintf(pci_path, sizeof(pci_path), "/proc/bus/pci/%s", bus_dev);
  pci_fd = open(pci_path, O_RDWR);
  if (pci_fd < 0) {
    ERROR("cannot open `%s': %m\n", pci_path);
    goto out;
  }

  ctl = 0x10100UL; // enable freeze (bit 16), freeze (bit 8)
  if (pwrite(pci_fd, &ctl, sizeof(ctl), HAU_BOX_CTL) < 0) {
    ERROR("cannot enable freeze of HAU counters: %m\n");
    goto out;
  }
  
  /* Select Events for HAU counters, HAU_CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", HAU_CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), HAU_CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) HAU_CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  /* HAU Counters must be manually reset */

  /* Manually reset programmable HAU counters. They are 4 apart, but each counter register is split into 2 32-bit registers, A and B */
  int zero = 0x0UL;
  for (i = 0; i < nr_events; i++) {
    if (pwrite(pci_fd, &zero, sizeof(zero), HAU_A_CTR0 + 8*i) < 0 || 
	pwrite(pci_fd, &zero, sizeof(zero), HAU_B_CTR0 + 8*i) < 0) { 
      ERROR("cannot reset counter %08X,%08X through `%s': %m\n", 
	    (unsigned) HAU_A_CTR0 + 8*i, (unsigned) HAU_B_CTR0 + 8*i,
            pci_path);
      goto out;
    }
  }
  
  ctl = 0x10000UL; // unfreeze counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), HAU_BOX_CTL) < 0) {
    ERROR("cannot unfreeze HAU counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

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
    if (intel_snb_hau_begin_dev(dev_paths[i], events, 4) == 0)
      nr++;   
  
  if (nr == 0)
    type->st_enabled = 0;

  return nr > 0 ? 0 : -1;
}

static void intel_snb_hau_collect_dev(struct stats_type *type, char *bus_dev)
{
  struct stats *stats = NULL;
  char pci_path[80];
  int pci_fd = -1;

  stats = get_current_stats(type, bus_dev);
  if (stats == NULL)
    goto out;

  TRACE("bus/dev %s\n", bus_dev);

  snprintf(pci_path, sizeof(pci_path), "/proc/bus/pci/%s", bus_dev);
  pci_fd = open(pci_path, O_RDONLY);
  if (pci_fd < 0) {
    ERROR("cannot open `%s': %m\n", pci_path);
    goto out;
  }

#define X(k,r...) \
  ({ \
    uint32_t val; \
    if ( pread(pci_fd, &val, sizeof(val), HAU_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, HAU_##k, pci_path); \
    else \
      stats_set(stats, #k, val);	\
  })
  CTL_KEYS;
#undef X

#define X(k,r...) \
  ({ \
    uint32_t val_a, val_b; \
    uint64_t val = 0x0ULL; \
    if ( pread(pci_fd, &val_a, sizeof(val_a), HAU_A_##k) < 0 || pread(pci_fd, &val_b, sizeof(val_b), HAU_B_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X,%08X) through `%s': %m\n", #k, HAU_A_##k, HAU_B_##k, pci_path); \
    else \
      val = val_a; stats_set(stats, #k, (val<<32) + val_b);	\
  })
  CTR_KEYS;
#undef X

 out:
  if (pci_fd >= 0)
    close(pci_fd);
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
    intel_snb_hau_collect_dev(type, dev_paths[i]);  
}

struct stats_type intel_snb_hau_stats_type = {
  .st_name = "intel_snb_hau",
  .st_begin = &intel_snb_hau_begin,
  .st_collect = &intel_snb_hau_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
