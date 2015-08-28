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

static int intel_snb_qpi_begin_dev(char *bus_dev, uint32_t *events, 
				   size_t nr_events)
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

  ctl = 0x10103UL; // enable freeze (bit 16), freeze (bit 8), reset counters
  if (pwrite(pci_fd, &ctl, sizeof(ctl), BOX_CTL) < 0) {
    ERROR("cannot enable freeze of QPI counters: %m\n");
    goto out;
  }
  
  /* Select Events for QPI counters, CTLx registers are 4 bits apart */
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

  ctl = 0x10000UL; // unfreeze counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), BOX_CTL) < 0) {
    ERROR("cannot unfreeze QPI counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_snb_qpi_begin(struct stats_type *type)
{
  int nr = 0;

  uint32_t events[] = {
    TxL_FLITS_G1_SNP,  TxL_FLITS_G1_HOM, G1_DRS_DATA, G2_NCB_DATA,   
  };
  int dids[] = {0x3c41, 0x3c42};

  char **dev_paths = NULL;
  int nr_devs;

  if (pci_map_create(&dev_paths, &nr_devs, dids, 2) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    if (intel_snb_qpi_begin_dev(dev_paths[i], events, 4) == 0)
      nr++; /* HARD */    
  
  if (nr == 0)
    type->st_enabled = 0;

  return nr > 0 ? 0 : -1;

}

static void intel_snb_qpi_collect(struct stats_type *type)
{
  int dids[] = {0x3c41, 0x3c42};

  char **dev_paths = NULL;
  int nr_devs;
  if (pci_map_create(&dev_paths, &nr_devs, dids, 2) < 0)
    TRACE("Failed to identify pci devices");
  
  int i;
  for (i = 0; i < nr_devs; i++)
    intel_snb_uncore_collect_dev(type, dev_paths[i]);  
}


struct stats_type intel_snb_qpi_stats_type = {
  .st_name = "intel_snb_qpi",
  .st_begin = &intel_snb_qpi_begin,
  .st_collect = &intel_snb_qpi_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
