/*! 
 \file intel_hsw_r2pci.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Ring to PCIe Interface (R2PCI)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 327043-001 March 2012 \n
  R2PCI monitoring is described in Section 2.8.

  \note
  Sandy Bridge microarchitectures have signatures 06_2a and 06_2d. 
  Stampede is 06_2d.


  \par Location of monitoring register files

  ex) Display PCI Config Space addresses:

      $ lspci | grep "Ring to PCI"
      7f:13.1 Performance counters: Intel Corporation Xeon E5/Core i7 Ring to PCI Express Performance Monitor (rev 07)
      ff:13.1 Performance counters: Intel Corporation Xeon E5/Core i7 Ring to PCI Express Performance Monitor (rev 07)


   \par PCI address layout of registers:

   ~~~
   PCI Config Space Dev ID:
   Socket 1: 7f:13.1
   Socket 0: ff:13.1
   ~~~
   
   Layout shown in Table 2-104.
   1 R2PCI w/ 4 counters each per socket
   
   There are 4 configure and 4 counter registers per R2PCI
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
#include "check_pci_id.h"
#include "pci_busid_map.h"

/*! \name R2PCI Global Control Register

  Layout in Table 2-105.  This register controls every R2PCI performance counter.  It can
  reset and freeze the counters.
*/
#define R2PCI_BOX_CTL        0xF4

/*! \name R2PCI Configurable Performance Monitoring Registers

  Control register layout in Table 2-106.  These are used to select events.  There are 4 per 
  socket, 4 per R2PCI.

  ~~~
  threshhold        [31:24]
  invert threshold  [23]
  enable            [22]
  edge detect       [18]
  umask             [15:8]
  event select      [7:0]
  ~~~

  \note
  Counter registers are 64 bits with 44 used for counting.  They actually must be read from 
  2 32 bit registers, with the first 32 (B) bits least and last 32 (A) bits most  significant.
  @{
*/
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
//@}

/*! \name KEYS will define the raw schema for this type. 
  
  The required order of registers is:
  -# Control registers in order
  -# Counter registers in order
  @{
*/
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
//@}

/*! \brief Event select
  
  Events are listed in Table 2-108.  They are defined in detail
  in Section 2.8.7.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_hsw_r2pci_begin()
*/
#define R2PCI_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 17) /* reset counter */ \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  | (0x01UL << 24) /* Threshold */ \
  )

/*! \name Events

  Events are listed in Table 2-108.  They are defined in detail
  in Section 2.8.7.

@{
 */
#define TxR_INSERTS      R2PCI_PERF_EVENT(0x24,0x04)  //!< CTR0 only
#define CLOCKTICKS       R2PCI_PERF_EVENT(0x01,0x00)
#define RING_AD_USED_ALL R2PCI_PERF_EVENT(0x07,0x0F)
#define RING_AK_USED_ALL R2PCI_PERF_EVENT(0x08,0x0F) 
#define RING_BL_USED_ALL R2PCI_PERF_EVENT(0x09,0x0F) 
//@}

static int intel_hsw_r2pci_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
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

static int intel_hsw_r2pci_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t r2pci_events[1][4] = {
    { TxR_INSERTS, RING_BL_USED_ALL, RING_AD_USED_ALL, RING_AK_USED_ALL},
  };

  /* 2-4 buses and 1 device per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  char *dev[1] = {"10.1"};
  int   ids[1] = {0x2f34};
  char bus_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 1; j++) {

      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      
      if (check_pci_id(bus_dev, ids[j]))
	if (intel_hsw_r2pci_begin_dev(bus_dev, r2pci_events[j], 4) == 0)
	  nr++; /* HARD */
    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_hsw_r2pci_collect_dev(struct stats_type *type, char *bus_dev, char* socket_dev)
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

static void intel_hsw_r2pci_collect(struct stats_type *type)
{
  /* 2-4 buses and 1 device per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  char *dev[1] = {"10.1"};
  int   ids[1] = {0x2f34};
  char bus_dev[80];                                        
  char socket_dev[80];
  
  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 1; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);      
      snprintf(socket_dev, sizeof(socket_dev), "%d/%s", i, dev[j]);      
      if (check_pci_id(bus_dev, ids[j]))
	intel_hsw_r2pci_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_hsw_r2pci_stats_type = {
  .st_name = "intel_hsw_r2pci",
  .st_begin = &intel_hsw_r2pci_begin,
  .st_collect = &intel_hsw_r2pci_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
