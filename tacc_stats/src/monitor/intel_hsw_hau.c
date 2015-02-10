/*! 
 \file intel_hsw_hau.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Home Agent Unit (HAU)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 331051 September 2014 \n
  HAU monitoring is described in Section 2.5.

  \note
  Haswell EP microarchitectures have signatures 06_3f.

  \par Location of monitoring register files

  ex) Display PCI Config Space addresses:

      $ lspci | grep "Home"
      7f:0e.0 System peripheral: Intel Corporation Xeon E5/Core i7 Processor Home Agent (rev 07)
      7f:0e.1 Performance counters: Intel Corporation Xeon E5/Core i7 Processor Home Agent Performance Monitoring (rev 07)
      ff:0e.0 System peripheral: Intel Corporation Xeon E5/Core i7 Processor Home Agent (rev 07)
      ff:0e.1 Performance counters: Intel Corporation Xeon E5/Core i7 Processor Home Agent Performance Monitoring (rev 07)


   \par PCI address layout of registers:

   ~~~
   PCI Config Space Dev ID:
   Socket 1: 7f:0e.1
   Socket 0: ff:0e.1
   ~~~
   
   Layout shown in Table 2-33.
   1 HAU w/ 4 counters each per socket
   
   There are 4 configure, 4 counter, 3 filter registers per HAU
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

/*! \name HAU Global Control Register

  Layout in Table 2-61.  This register controls every HAU performance counter.  It can
  reset and freeze the counters.
*/
#define HAU_BOX_CTL        0xF4

/*! \name HAU Configurable Performance Monitoring Registers

  Control register layout in Table 2-35.  These are used to select events.  There are 4 per 
  socket, 4 per HAU.

  ~~~
  threshhold        [31:24]
  invert threshold  [23]
  enable            [22]
  edge detect       [18]
  umask             [15:8]
  event select      [7:0]
  ~~~

  \note
  Counter registers are 64 bits with 48 used for counting.  They actually must be read from 
  2 32 bit registers, with the first 32 (B) bits least and last 32 (A) bits most  significant.
  @{
*/
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
//@}

/*! \name HAU filter registers

  These are not currently used in tacc_stats.
  Allow filtering by opcode and address.
  @{
 */
#define HAU_ADRRMATCH0     0x40
#define HAU_ADDRMATCH1     0x44
#define HAU_OPCODEMATCH    0x48
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
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", "")

#define KEYS CTL_KEYS, CTR_KEYS
//@}

/*! \brief Event select
  
  Events are listed in Table 2-40.  They are defined in detail
  in Section 2.5.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_hsw_hau_begin()
*/
#define HAU_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 18) \
  | (1UL << 22) \
  | (0UL << 23) \
  | (0x01UL << 24) \
  )

/*! \name Events

  Events are listed in Table 2-40.  They are defined in detail
  in Section 2.4.7.

@{
 */
#define REQUESTS_READS  HAU_PERF_EVENT(0x01,0x03)
#define REQUESTS_WRITES HAU_PERF_EVENT(0x01,0x0C)
#define CLOCKTICKS      HAU_PERF_EVENT(0x00,0x00)
#define IMC_WRITES      HAU_PERF_EVENT(0x1A,0x0F) 
//@}

static int intel_hsw_hau_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
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

  ctl = 0x00103UL; // freeze (bit 8) reset (bits 1,0)
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
  
  ctl = 0x00000UL; // unfreeze counter
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

static int intel_hsw_hau_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t hau_events[2][4] = {
    { REQUESTS_READS, REQUESTS_WRITES, CLOCKTICKS, IMC_WRITES},
    { REQUESTS_READS, REQUESTS_WRITES, CLOCKTICKS, IMC_WRITES},
  };

  /* 2-4 buses and 2 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);
  char *dev[2] = {"12.1", "12.5"};
  int   ids[2] = {0x2f30, 0x2f38};
  char bus_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 2; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);      
      if (check_pci_id(bus_dev,ids[j]))
	if (intel_hsw_hau_begin_dev(bus_dev, hau_events[j], 4) == 0)
	  nr++; /* HARD */    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_hsw_hau_collect_dev(struct stats_type *type, char *bus_dev, char *socket_dev)
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

static void intel_hsw_hau_collect(struct stats_type *type)
{
  /* 2-4 buses and 2 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);
  char *dev[2] = {"12.1", "12.5"};
  int   ids[2] = {0x2f30, 0x2f38};
  char bus_dev[80];       
  char socket_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 2; j++) {

      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      snprintf(socket_dev, sizeof(socket_dev), "%d/%s", i, dev[j]);
      if (check_pci_id(bus_dev,ids[j]))
	intel_hsw_hau_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_hsw_hau_stats_type = {
  .st_name = "intel_hsw_hau",
  .st_begin = &intel_hsw_hau_begin,
  .st_collect = &intel_hsw_hau_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
