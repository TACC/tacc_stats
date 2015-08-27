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

/*! \name R2PCI Global Control Register */
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
    if (intel_snb_r2pci_begin_dev(dev_paths[i], events, 4) == 0)
      nr++; /* HARD */    

  if (nr == 0)
    type->st_enabled = 0;

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
  int ids[] = {0x3c43};

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, 1) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_r2pci_collect_dev(type, dev_paths[i]);  
}

struct stats_type intel_snb_r2pci_stats_type = {
  .st_name = "intel_snb_r2pci",
  .st_begin = &intel_snb_r2pci_begin,
  .st_collect = &intel_snb_r2pci_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
