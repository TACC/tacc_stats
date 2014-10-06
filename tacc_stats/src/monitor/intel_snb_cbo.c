/*! 
 \file intel_snb_cbo.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Caching Agents (CBos)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 327043-001 March 2012 \n
  CBo monitoring is described in Section 2.3.

  \note
  Sandy Bridge microarchitectures have signatures 06_2a and 06_2d. 
  Stampede is 06_2d.


  \par Location of cpu info and monitoring register files:

  ex) Display cpuid and msr file for cpu 0:

      $ ls -l /dev/cpu/0
      total 0
      crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
      crw-------  1 root root 202, 0 Oct 28 18:47 msr


   \par MSR address layout of registers:

   Layout shown in Table 2-8.
   There are 8 CBos per socket, and currently 2 sockets on Stampede.
   There are 4 configurable counter registers per CBo.  These routines
   only collect data on core_id 0 on each socket.
   
   There are 4 configure, 4 counter, 1  CBo global control, 
   and 1 CBo filter registers per CBo
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
#include "cpu_is_snb.h"

/*! \name CBo Performance Monitoring Global Control Registers

   Configure register layout shown in Table 2-9.  These registers control every
   counter within a CBo.  They can freeze and reset 
   individual CBos control and counter registers.

   \note
   Documentation says they are 32 bit but only 64 bit
   works.

   @{
*/

#define CBOX_CTL0 0xD04
#define CBOX_CTL1 0xD24
#define CBOX_CTL2 0xD44
#define CBOX_CTL3 0xD64
#define CBOX_CTL4 0xD84
#define CBOX_CTL5 0xDA4
#define CBOX_CTL6 0xDC4
#define CBOX_CTL7 0xDE4
//@}

/*! \name CBo filter registers

  Layout in Table 2-12. Can filter CBo counters' recorded events by 
  Opcode, MESIF state, core, and/or Hyperthread.
  
  ~~~
  opcode             [31:23]
  state              [22:18]
  node               [17:10]
  core               [3:1] 
  thread             [0] 
  ~~~  

  Opcodes are listed in Table 2-13 and defined in
  Table 2-144.

  \note
  Documentation says they are 32 bit but only 64 bit
  works.
  @{
 */
#define CBOX_FILTER0 0xD14
#define CBOX_FILTER1 0xD34
#define CBOX_FILTER2 0xD54
#define CBOX_FILTER3 0xD74
#define CBOX_FILTER4 0xD94
#define CBOX_FILTER5 0xDB4
#define CBOX_FILTER6 0xDD4
#define CBOX_FILTER7 0xDF4
//@}

/*! \name CBo Performance Monitoring Registers
  
  Control register layout in 2-10.  These are used to select events.  There are
  32 total per socket, 4 per CBo.  We specify base address and increment by 
  1 intra-CBo and 32 inter-CBo.
  ~~~
  threshhold        [31:24]
  invert threshold  [23]
  enable            [22]
  tid filter enable [19]
  edge detect       [18]
  clear counter     [17]
  umask             [15:8]
  event select      [7:0]
  ~~~ 

  \note
  Documentation says they are 32 bit but only 64 bit
  works.

  Counter register layout in 2-11.  These are 64 bit but counters
  are only 44 bits wide.

  @{
 */
#define CTL0 0xD10
#define CTL1 0xD11
#define CTL2 0xD12
#define CTL3 0xD13

#define CTR0 0xD16
#define CTR1 0xD17
#define CTR2 0xD18
#define CTR3 0xD19
//@}

/*! \brief KEYS will define the raw schema for this type. 
  
  The required order of registers is:
  -# Control registers in order
  -# Counter registers in order
*/
#define KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", ""),  \
    X(CTR0, "E,W=44", ""), \
    X(CTR1, "E,W=44", ""), \
    X(CTR2, "E,W=44", ""), \
    X(CTR3, "E,W=44", "")

/*! \brief Filter 
  
  Can filter by opcode, MESIF state, node, core, thread
 */
#define CBOX_FILTER(...)  \
  ( (0x0ULL << 0)  \
  | (0x00ULL << 10) \
  | (0x1FULL << 18)  \
  | (0x000ULL << 23) \
  )

/*! \brief Event select
  
  Events are listed in Table 2-14.  They are defined in detail
  in Section 2.3.7.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_snb_cbo_begin()
*/
#define CBOX_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0ULL << 17) \
  | (0ULL << 18) \
  | (0ULL << 19) \
  | (1ULL << 22) \
  | (0ULL << 23) \
  | (0x01ULL << 24) \
  )

/*! \name Events

  Events are listed in Table 2-14.  They are defined in detail
  in Section 2.3.7.  Some events can only be counted on
  specific registers.

@{
 */
#define CLOCK_TICKS         CBOX_PERF_EVENT(0x00, 0x00) //!< CTR0-3
#define RxR_OCCUPANCY       CBOX_PERF_EVENT(0x11, 0x01) //!< CTR0
#define COUNTER0_OCCUPANCY  CBOX_PERF_EVENT(0x1F, 0x00) //!< CTR1-3
#define LLC_LOOKUP          CBOX_PERF_EVENT(0x34, 0x03) //!< CTR0-1
//@}

//! Configure and start counters for CBo
static int intel_snb_cbo_begin_box(char *cpu, int box, uint64_t *events, size_t nr_events)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t ctl;
  uint64_t filter;
  int offset = box*32;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  ctl = 0x10100ULL; // enable freeze (bit 16), freeze (bit 8)
  /* CBo ctrl registers are 32-bits apart */
  if (pwrite(msr_fd, &ctl, sizeof(ctl), CBOX_CTL0 + offset) < 0) {
    ERROR("cannot enable freeze of CBo counter: %m\n");
    goto out;
  }

  /* Filtering by opcode, MESIF state, node, core and thread possible */
  filter = CBOX_FILTER();
  if (pwrite(msr_fd, &filter, sizeof(filter), CBOX_FILTER0 + offset) < 0) {
    ERROR("cannot modify CBo filters: %m\n");
    goto out;
  }

  /* Select Events for this C-Box */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", CTL0 + offset + i, (unsigned long long) events[i]);
    if (pwrite(msr_fd, &events[i], sizeof(events[i]), CTL0 + offset + i) < 0) { 
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n", 
            (unsigned long long) events[i],
            (unsigned) CTL0 + offset + i,
            msr_path);
      goto out;
    }
  }

  ctl |= 1ULL << 1; // reset counter
  /* CBo ctrl registers are 32-bits apart */
  if (pwrite(msr_fd, &ctl, sizeof(ctl), CBOX_CTL0 + offset) < 0) {
    ERROR("cannot reset CBo counter: %m\n");
    goto out;
  }
  
  /* Unfreeze CBo counter (64-bit) */
  ctl = 0x10000ULL; // unfreeze counter
  if (pwrite(msr_fd, &ctl, sizeof(ctl), CBOX_CTL0 + offset) < 0) {
    ERROR("cannot unfreeze CBo counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}


//! Configure and start counters
static int intel_snb_cbo_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t cbo_events[8][4] = {
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
    { RxR_OCCUPANCY, LLC_LOOKUP, COUNTER0_OCCUPANCY, CLOCK_TICKS, },
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];
    int core_id = -1;
    int box;
    /* Only program uncore counters on core 0 of a socket. */

    snprintf(core_id_path, sizeof(core_id_path), "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path); /* errno */
      continue;
    }

    if (core_id != 0)
      continue;

    snprintf(cpu, sizeof(cpu), "%d", i);
    
    if (cpu_is_sandybridge(cpu))      
      {
	for (box = 0; box < 8; box++)
	  if (intel_snb_cbo_begin_box(cpu, box, cbo_events[box], 4) == 0)
	    nr++;
      }
  }

  return nr > 0 ? 0 : -1;
}

//! Collect values in counters for a CBo
static void intel_snb_cbo_collect_box(struct stats_type *type, char *cpu, char* cpu_box, int box)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;
  int offset;
  offset = 32*box;

  stats = get_current_stats(type, cpu_box);
  if (stats == NULL)
    goto out;

  TRACE("cpu %s\n", cpu);
  TRACE("socket/box %s\n", cpu_box);

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

#define X(k,r...) \
  ({ \
    uint64_t val = 0; \
    if (pread(msr_fd, &val, sizeof(val), k + offset) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, k + offset, msr_path); \
    else \
      stats_set(stats, #k, val); \
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

//! Collect values in counters
static void intel_snb_cbo_collect(struct stats_type *type)
{

  int i;

  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];

    char socket[80];
    char socket_id_path[80];

    char cpu_box[80];

    int socket_id = -1;
    int core_id = -1;
    int box;

    /* Only collect uncore counters on core 0 of a socket. */
    snprintf(core_id_path, sizeof(core_id_path), 
	     "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path);
      continue;
    }
    if (core_id != 0)
      continue;

    /* Get socket number. */
    snprintf(socket_id_path, sizeof(socket_id_path), 
	     "/sys/devices/system/cpu/cpu%d/topology/physical_package_id", i);
    if (pscanf(socket_id_path, "%d", &socket_id) != 1) {
      ERROR("cannot read socket id file `%s': %m\n", socket_id_path);
      continue;
    }

    snprintf(cpu, sizeof(cpu), "%d", i);
    snprintf(socket, sizeof(socket), "%d", socket_id);

    if (cpu_is_sandybridge(cpu))
      {
	for (box = 0; box < 8; box++)
	  {
	    snprintf(cpu_box, sizeof(cpu_box), "%d/%d", socket_id, box);
	    intel_snb_cbo_collect_box(type, cpu, cpu_box, box);
	  }
      }
  }
}

//! Definition of stats for this type
struct stats_type intel_snb_cbo_stats_type = {
  .st_name = "intel_snb_cbo",
  .st_begin = &intel_snb_cbo_begin,
  .st_collect = &intel_snb_cbo_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
