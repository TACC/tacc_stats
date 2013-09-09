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

// Uncore Home Agent Unit events are counted in this file.  The events are accesses in PCI config space.

// Sandy Bridge microarchitectures have signatures 06_2a and 06_2d with non-architectural events
// listed in Table 19-7, 19-8, and 19-9.  19-8 is 06_2a specific, 19-9 is 06_2d specific.  Stampede
// is 06_2d but no 06_2d specific events are used here.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// $ lspci | grep "HOME"
/*
7f:0e.0 System peripheral: Intel Corporation Xeon E5/Core i7 Processor Home Agent (rev 07)
7f:0e.1 Performance counters: Intel Corporation Xeon E5/Core i7 Processor Home Agent Performance Monitoring (rev 07)
ff:0e.0 System peripheral: Intel Corporation Xeon E5/Core i7 Processor Home Agent (rev 07)
ff:0e.1 Performance counters: Intel Corporation Xeon E5/Core i7 Processor Home Agent Performance Monitoring (rev 07)
*/

// Info for this stuff is in: 
//Intel Xeon Processor E5-2600 Product Family Uncore Performance Monitoring Guide
// 1 Home Agent Units with four counters
// PCI Config Space Dev ID:
// Socket 1: 7f:0e.1
// Socket 0: ff:0e.1
// Supposedly all registers are 32 bit, but counter
// registers A and B need to be added to get counter value

// Defs in Table 2-33
#define HAU_BOX_CTL        0xF4

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


// Width of 44 for QPI Counters
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

/* Event Selection in HAU
threshhold        [31:24]
invert threshold  [23]
enable            [22]
edge detect       [18]
umask             [15:8]
event select      [7:0]
*/

/* Defs in Table 2-61 */
#define HAU_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  | (0x01UL << 24) /* Threshold */ \
  )

/* Definitions in Table 2-94 */
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
  
  uint32_t hau_events[1][4] = {
    { REQUESTS_READS, REQUESTS_WRITES, CLOCKTICKS, IMC_WRITES},
  };

  /* 2 buses and 1 device per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[1] = {"0e.1"};
  int   ids[1] = {0x3c46};
  char bus_dev[80];

  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 1; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);      
      if (check_pci_id(bus_dev,ids[j]))
	if (intel_snb_hau_begin_dev(bus_dev, hau_events[j], 4) == 0)
	  nr++; /* HARD */    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_hau_collect_dev(struct stats_type *type, char *bus_dev, char *socket_dev)
{
  struct stats *stats = NULL;
  char pci_path[80];
  int pci_fd = -1;

  stats = get_current_stats(type, socket_dev);
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
  /* 2 buses and 1 device per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[1] = {"0e.1"};
  int   ids[1] = {0x3c46};
  char bus_dev[80];       
  char socket_dev[80];

  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 1; j++) {

      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      snprintf(socket_dev, sizeof(socket_dev), "%d/%d", i, j);
      if (check_pci_id(bus_dev,ids[j]))
	intel_snb_hau_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_snb_hau_stats_type = {
  .st_name = "intel_snb_hau",
  .st_begin = &intel_snb_hau_begin,
  .st_collect = &intel_snb_hau_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
