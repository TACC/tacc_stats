/*! 
 \file intel_hsw_qpi.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge QPI Link Layer (QPI)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 327043-001 March 2012 \n
  QPI monitoring is described in Section 2.7.

  \note
  Sandy Bridge microarchitectures have signatures 06_2a and 06_2d. 
  Stampede is 06_2d.


  \par Location of monitoring register files

  ex) Display PCI Config Space addresses:

       $ lspci -nn | grep "Performance counters"
       7f:08.2 Performance counters [1101]: Intel Corporation Device [8086:3c41] (rev 07)
       7f:09.2 Performance counters [1101]: Intel Corporation Device [8086:3c42] (rev 07)
       ff:08.2 Performance counters [1101]: Intel Corporation Device [8086:3c41] (rev 07)
       ff:09.2 Performance counters [1101]: Intel Corporation Device [8086:3c42] (rev 07)

   \par PCI address layout of registers:

   ~~~
   PCI Config Space Dev ID:
   Socket 1: 7f:08.2, 7f:09.2
   Socket 0: ff:08.5, 7f:09.2
   ~~~
   
   Layout shown in Table 2-84.
   2 QPI w/ 4 counters each per socket
   
   There are 4 configure, 4 counter, 1 mask and 1 match per QPI.
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

/*! \name QPI Global Control Register

  Layout in Table 2-85.  This register controls every QPI performance counter.  It can
  reset and freeze the counters.
*/
#define QPI_BOX_CTL  0xF4

/*! \name QPI Configurable Performance Monitoring Registers

  Control register layout in Table 2-86.  These are used to select events.  There are 8 per 
  socket, 4 per QPI.

  ~~~
  threshhold        [31:24]
  invert threshold  [23]
  enable            [22]
  event ext         [21]
  edge detect       [18]
  reset             [17]
  umask             [15:8]
  event select      [7:0]
  ~~~

  \note
  Counter registers are 64 bits with 48 used for counting.  They actually must be read from 
  2 32 bit registers, with the first 32 (B) bits least and last 32 (A) bits most  significant.
  @{
*/
#define QPI_CTL0     0xD8
#define QPI_CTL1     0xDC
#define QPI_CTL2     0xE0
#define QPI_CTL3     0xE4

#define QPI_B_CTR0   0xA0
#define QPI_A_CTR0   0xA4
#define QPI_B_CTR1   0xA8
#define QPI_A_CTR1   0xAC
#define QPI_B_CTR2   0xB0
#define QPI_A_CTR2   0xB4
#define QPI_B_CTR3   0xB8
#define QPI_A_CTR3   0xBC
//@}

/*! \name QPI filter registers

  These are not currently used in tacc_stats.
  Allow filtering by opcode and address.
  @{
 */
#define QPI_MASK0    0x238
#define QPI_MASK1    0x23C
#define QPI_MATCH0   0x228
#define QPI_MATCH1   0x22C
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
    X(CTR0, "E,W=48,U=flt", ""), \
    X(CTR1, "E,W=48,U=flt", ""), \
    X(CTR2, "E,W=48,U=flt", ""), \
    X(CTR3, "E,W=48,U=flt", "")

#define KEYS CTL_KEYS, CTR_KEYS
//@}

/*! \brief Event select
  
  Events are listed in Table 2-94.  They are defined in detail
  in Section 2.7.7.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_hsw_qpi_begin()
*/
#define QPI_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 21) /* Enable extra bit. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  )

/*! \name Events

  Events are listed in Table 2-40.  They are defined in detail
  in Section 2.4.7.

@{
 */
#define TxL_FLITS_G1_SNP  QPI_PERF_EVENT(0x00,0x01) //!< snoops requests
#define TxL_FLITS_G1_HOM  QPI_PERF_EVENT(0x00,0x04) //!< snoop responses
#define G1_DRS_DATA       QPI_PERF_EVENT(0x02,0x08) //!< for data bandwidth, flits x 8B/time
#define G2_NCB_DATA       QPI_PERF_EVENT(0x03,0x04) //!< for data bandwidth, flits x 8B/time
//@}

static int intel_hsw_qpi_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
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
  if (pwrite(pci_fd, &ctl, sizeof(ctl), QPI_BOX_CTL) < 0) {
    ERROR("cannot enable freeze of QPI counters: %m\n");
    goto out;
  }
  
  /* Select Events for QPI counters, QPI_CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", QPI_CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), QPI_CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) QPI_CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  ctl = 0x10000UL; // unfreeze counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), QPI_BOX_CTL) < 0) {
    ERROR("cannot unfreeze QPI counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_hsw_qpi_begin(struct stats_type *type)
{
  int nr = 0;

  uint32_t qpi_events[2][4] = {
    { TxL_FLITS_G1_SNP,  TxL_FLITS_G1_HOM, G1_DRS_DATA, G2_NCB_DATA},
    { TxL_FLITS_G1_SNP,  TxL_FLITS_G1_HOM, G1_DRS_DATA, G2_NCB_DATA},
  };

  /* 2-4 buses and 4 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  char *dev[2] = {"08.2", "09.2"};
  int   ids[2] = {0x2f32, 0x2f33};
  char bus_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 2; j++) {

      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      
      if (check_pci_id(bus_dev, ids[j]))
	if (intel_hsw_qpi_begin_dev(bus_dev, qpi_events[j], 4) == 0)
	  nr++; /* HARD */
    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_hsw_qpi_collect_dev(struct stats_type *type, char *bus_dev, char *socket_dev)
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
    if ( pread(pci_fd, &val, sizeof(val), QPI_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, QPI_##k, pci_path); \
    else \
      stats_set(stats, #k, val);	\
  })
  CTL_KEYS;
#undef X

#define X(k,r...) \
  ({ \
    uint32_t val_a, val_b; \
    uint64_t val = 0x0ULL; \
    if ( pread(pci_fd, &val_a, sizeof(val_a), QPI_A_##k) < 0 || pread(pci_fd, &val_b, sizeof(val_b), QPI_B_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X,%08X) through `%s': %m\n", #k, QPI_A_##k, QPI_B_##k, pci_path); \
    else \
      val = val_a; stats_set(stats, #k, (val<<32) + val_b);	\
  })
  CTR_KEYS;
#undef X

 out:
  if (pci_fd >= 0)
    close(pci_fd);
}

static void intel_hsw_qpi_collect(struct stats_type *type)
{
  /* 2-4 buses and 4 devices per bus */
  char **bus;
  int num_buses;
  num_buses = get_pci_busids(&bus);

  char *dev[2] = {"08.2", "09.2"};
  int   ids[2] = {0x2f32, 0x2f33};
  char bus_dev[80];                                        
  char socket_dev[80];

  int i, j;
  for (i = 0; i < num_buses; i++) {
    for (j = 0; j < 2; j++) {
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      snprintf(socket_dev, sizeof(socket_dev), "%d/%s", i, dev[j]);
      
      if (check_pci_id(bus_dev, ids[j]))
	intel_hsw_qpi_collect_dev(type, bus_dev, socket_dev);
    }
  }
}

struct stats_type intel_hsw_qpi_stats_type = {
  .st_name = "intel_hsw_qpi",
  .st_begin = &intel_hsw_qpi_begin,
  .st_collect = &intel_hsw_qpi_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
