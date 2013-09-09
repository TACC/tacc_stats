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

// Uncore R2PCIe Unit events are counted in this file.  The events are accesses in PCI config space.

// Sandy Bridge microarchitectures have signatures 06_2a and 06_2d with non-architectural events
// listed in Table 19-7, 19-8, and 19-9.  19-8 is 06_2a specific, 19-9 is 06_2d specific.  Stampede
// is 06_2d but no 06_2d specific events are used here.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// $ lspci | grep "Ring to PCI"
/*
7f:13.1 Performance counters: Intel Corporation Xeon E5/Core i7 Ring to PCI Express Performance Monitor (rev 07)
ff:13.1 Performance counters: Intel Corporation Xeon E5/Core i7 Ring to PCI Express Performance Monitor (rev 07)
*/

// Info for this stuff is in: 
// Intel Xeon Processor E5-2600 Product Family Uncore Performance Monitoring Guide

// 1 Home Agent Units with four counters
// PCI Config Space Dev ID:
// Socket 1: 7f:13.1
// Socket 0: ff:13.1

// Supposedly all registers are 32 bit, but counter
// registers A and B need to be added to get counter value

// Defs in Table 2-104
#define R2PCI_BOX_CTL        0xF4

#define R2PCI_CTL0           0xD8
#define R2PCI_CTL1           0xDC
#define R2PCI_CTL2           0xE0
#define R2PCI_CTL3           0xE4

#define R2PCI_B_CTR0         0xA0
#define R2PCI_A_CTR0         0xA4
#define R2PCI_B_CTR1         0xA8
#define R2PCI_A_CTR1         0xAC
#define R2PCI_B_CTR2         0xB0
#define R2PCI_A_CTR2         0xB4
#define R2PCI_B_CTR3         0xB8
#define R2PCI_A_CTR3         0xBC

// Width of 44 for R2PCI Counter Registers
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

/* Event Selection in R2PCI
threshhold        [31:24]
invert threshold  [23]
enable            [22]
edge detect       [18]
umask             [15:8]
event select      [7:0]
*/

/* Defs in Table 2-106 */
#define R2PCI_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 17) /* reset counter */ \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  | (0x01UL << 24) /* Threshold */ \
  )

/* Definitions in Table 2-108 */
#define TxR_INSERTS      R2PCI_PERF_EVENT(0x24,0x04)  /* Ctr 0 only */
#define CLOCKTICKS       R2PCI_PERF_EVENT(0x01,0x00)
#define RING_AD_USED_ALL R2PCI_PERF_EVENT(0x07,0x0F)
#define RING_AK_USED_ALL R2PCI_PERF_EVENT(0x08,0x0F) 
#define RING_BL_USED_ALL R2PCI_PERF_EVENT(0x09,0x0F) 

static int intel_snb_r2pci_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
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

  ctl = 0x10102UL; // enable freeze (bit 16), freeze (bit 8), reset counters
  if (pwrite(pci_fd, &ctl, sizeof(ctl), R2PCI_BOX_CTL) < 0) {
    ERROR("cannot enable freeze of R2PCI counters: %m\n");
    goto out;
  }
  
  /* Select Events for R2PCI counters, R2PCI_CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", R2PCI_CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), R2PCI_CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) R2PCI_CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  ctl = 0x10000UL; // unfreeze counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), R2PCI_BOX_CTL) < 0) {
    ERROR("cannot unfreeze R2PCI counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_snb_r2pci_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t r2pci_events[1][4] = {
    { TxR_INSERTS, RING_BL_USED_ALL, RING_AD_USED_ALL, RING_AK_USED_ALL},
  };

  /* 2 buses and 1 device per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[1] = {"13.1"};
  int   ids[1] = {0x3c43};
  char bus_dev[80];

  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 1; j++) {

      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      
      if (check_pci_id(bus_dev, ids[j]))
	if (intel_snb_r2pci_begin_dev(bus_dev, r2pci_events[j], 4) == 0)
	  nr++; /* HARD */
    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_r2pci_collect_dev(struct stats_type *type, char *bus_dev, char* socket_dev)
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

  /* Read Control Register - 32 bit */
#define X(k,r...) \
  ({ \
    uint32_t val; \
    if ( pread(pci_fd, &val, sizeof(val), R2PCI_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, R2PCI_##k, pci_path); \
    else \
      stats_set(stats, #k, val);	\
  })
  CTL_KEYS;
#undef X

  /* Read Counter Registers - 2x32 bit registers */
#define X(k,r...) \
  ({ \
    uint32_t val_a, val_b; \
    uint64_t val = 0x0ULL; \
    if ( pread(pci_fd, &val_a, sizeof(val_a), R2PCI_A_##k) < 0 || pread(pci_fd, &val_b, sizeof(val_b), R2PCI_B_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X,%08X) through `%s': %m\n", #k, R2PCI_A_##k, R2PCI_B_##k, pci_path); \
    else \
      val = val_a; stats_set(stats, #k, (val<<32) + val_b);	\
  })
  CTR_KEYS;
#undef X

 out:
  if (pci_fd >= 0)
    close(pci_fd);
}

static void intel_snb_r2pci_collect(struct stats_type *type)
{
  /* 2 buses and 1 device per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[1] = {"13.1"};
  int   ids[1] = {0x3c43};
  char bus_dev[80];                                        
  char socket_dev[80];
  
  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 1; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);      
      snprintf(socket_dev, sizeof(socket_dev), "%d/%d", i, j);      
      if (check_pci_id(bus_dev, ids[j]))
	intel_snb_r2pci_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_snb_r2pci_stats_type = {
  .st_name = "intel_snb_r2pci",
  .st_begin = &intel_snb_r2pci_begin,
  .st_collect = &intel_snb_r2pci_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
