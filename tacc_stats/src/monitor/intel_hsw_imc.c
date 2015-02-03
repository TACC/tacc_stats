/*! 
 \file intel_hsw_imc.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Integrated Memory Controller (iMC)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 327043-001 March 2012 \n
  iMC monitoring is described in Section 2.5.

  \note
  Sandy Bridge microarchitectures have signatures 06_2a and 06_2d. 
  Stampede is 06_2d.


  \par Location of monitoring register files

  ex) Display PCI Config Space addresses:

      $ lspci | grep "Memory Controller Channel"
      7f:10.0 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 0 (rev 07)
      7f:10.1 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 1 (rev 07)
      7f:10.4 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 2 (rev 07)
      7f:10.5 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 3 (rev 07)
      ff:10.0 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 0 (rev 07)
      ff:10.1 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 1 (rev 07)
      ff:10.4 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 2 (rev 07)
      ff:10.5 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 3 (rev 07)


   \par PCI address layout of registers:

   ~~~
   PCI Config Space Dev ID:
   Socket 1: 7f:10.0, 7f:10.1, 7f:10.4, 7f:10.5 
   Socket 0: ff:10.0, 7f:10.1, ff:10.4, ff:10.5 
   ~~~
   
   Layout shown in Table 2-59.
   4 iMCs w/ 4 counters each per socket
   
   There are 4 configure, 4 counter, 1  iMC global control, 
   and 1 fixed register per iMC
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

/*! \name iMC Global Control Register

Layout in Table 2-60.  This register controls every iMC performance counter.  It can
reset and freeze the counters.
*/
#define MC_BOX_CTL        0xF4

/*! \name iMC Configurable Performance Monitoring Registers

  Control register layout in Table 2-61.  These are used to select events.  There are 16 per 
  socket, 4 per iMC.

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
#define MC_CTL0           0xD8
#define MC_CTL1           0xDC
#define MC_CTL2           0xE0
#define MC_CTL3           0xE4

#define MC_B_CTR0         0xA0
#define MC_A_CTR0         0xA4
#define MC_B_CTR1         0xA8
#define MC_A_CTR1         0xAC
#define MC_B_CTR2         0xB0
#define MC_A_CTR2         0xB4
#define MC_B_CTR3         0xB8
#define MC_A_CTR3         0xBC
//@}

/*! \name iMC Fixed Counter

  Fixed control register layout in Table 2-62.  Enable and resets fixed counter.

  \note
  Counter registers are 64 bits with 48 used for counting.  They actually must be read from 
  2 32 bit registers, with the first 32 (B) bits least and last 32 (A) bits most  significant.
  
  Counts DRAM clock cycles.
  @{
 */
#define MC_FIXED_CTL      0xF0
#define MC_B_FIXED_CTR    0xD0
#define MC_A_FIXED_CTR    0xD4
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
#define ACT_COUNT           MBOX_PERF_EVENT(0x01, 0x00)
#define PRE_COUNT_ALL       MBOX_PERF_EVENT(0x02, 0x03)
#define PRE_COUNT_MISS       MBOX_PERF_EVENT(0x02, 0x01)
//@}

static int intel_hsw_imc_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
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

  ctl = 0x00103UL; // enable freeze (bit 16), freeze (bit 8)
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_BOX_CTL) < 0) {
    ERROR("cannot enable freeze of MC counters: %m\n");
    goto out;
  }
  
  ctl = 0x80000UL; // Reset Fixed Counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_FIXED_CTL) < 0) {
    ERROR("cannot undo reset of MC Fixed counter: %m\n");
    goto out;
  }
 
  /* Select Events for MC counters, MC_CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", MC_CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), MC_CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) MC_CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  /* Manually reset programmable MC counters. They are 4 apart, but each counter register is split into 2 32-bit registers, A and B */
  uint32_t zero = 0x0UL;
  for (i = 0; i < nr_events; i++) {
    if (pwrite(pci_fd, &zero, sizeof(zero), MC_A_CTR0 + 8*i) < 0 || 
	pwrite(pci_fd, &zero, sizeof(zero), MC_B_CTR0 + 8*i) < 0) { 
      ERROR("cannot reset counter %08X,%08X through `%s': %m\n", 
	    (unsigned) MC_A_CTR0 + 8*i, (unsigned) MC_B_CTR0 + 8*i,
            pci_path);
      goto out;
    }
  }

  ctl = 0x400000UL; // Enable Fixed Counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_FIXED_CTL) < 0) {
    ERROR("cannot undo reset of MC Fixed counter: %m\n");
    goto out;
  }
  
  ctl = 0x00000UL; // unfreeze counters
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_BOX_CTL) < 0) {
    ERROR("cannot unfreeze MC counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_hsw_imc_begin(struct stats_type *type)
{
  int nr = 0;

  uint32_t imc_events[4][4] = {
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_MISS,},
  };

  /* 2-4 buses and 4 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  char *dev[4] = {"14.0", "14.1", "17.0", "17.1"};
  int  ids[4] = {0x2fb0, 0x2fb1, 0x2fd0, 0x2fd1}; 
  char bus_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 4; j++) {
      // bus and device name
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      if (check_pci_id(bus_dev, ids[j]))
	if (intel_hsw_imc_begin_dev(bus_dev, imc_events[j], 4) == 0)
	  nr++; /* HARD */    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_hsw_imc_collect_dev(struct stats_type *type, char *bus_dev, char *socket_dev)
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
    if ( pread(pci_fd, &val, sizeof(val), MC_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, MC_##k, pci_path); \
    else \
      stats_set(stats, #k, val);	\
  })
  CTL_KEYS;
#undef X

#define X(k,r...) \
  ({ \
    uint32_t val_a, val_b; \
    uint64_t val = 0x0ULL; \
    if ( pread(pci_fd, &val_a, sizeof(val_a), MC_A_##k) < 0 || pread(pci_fd, &val_b, sizeof(val_b), MC_B_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X,%08X) through `%s': %m\n", #k, MC_A_##k, MC_B_##k, pci_path); \
    else \
      val = val_a; stats_set(stats, #k, (val<<32) + val_b);	\
  })
  CTR_KEYS;
#undef X

 out:
  if (pci_fd >= 0)
    close(pci_fd);
}

static void intel_hsw_imc_collect(struct stats_type *type)
{
  /* 2-4 buses and 4 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  //char *dev[4] = {"14.0", "14.1", "15.0", "15.1", "17.0", "17.1", "18.0", "18.1"};
  //int   ids[4] = {0x2fb4, 0x2fb5, 0x2fb0, 0x2fb1, 0x2fd4, 0x2fd5, 0x2fd0, 0x2fd1}; 
  char *dev[4] = {"14.0", "14.1", "17.0", "17.1"};
  int   ids[4] = {0x2fb0, 0x2fb1, 0x2fd0, 0x2fd1}; 
  char bus_dev[80];                                        
  char socket_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 4; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      snprintf(socket_dev, sizeof(socket_dev), "%d/%s", i, dev[j]);
      if (check_pci_id(bus_dev,ids[j]))
	intel_hsw_imc_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_hsw_imc_stats_type = {
  .st_name = "intel_hsw_imc",
  .st_begin = &intel_hsw_imc_begin,
  .st_collect = &intel_hsw_imc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
