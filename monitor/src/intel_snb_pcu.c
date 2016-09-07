/*! 
 \file intel_snb_pcu.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Power Control Unit (PCU)


  \par Details such as Tables and Figures can be found in:
  "Intel® Xeon® Processor E5-2600 Product Family Uncore 
  Performance Monitoring Guide" 
  Reference Number: 327043-001 March 2012 \n
  PCU monitoring is described in Section 2.6.

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

   Layout in Table 2-73.
   There is 1 PCU per socket, and currently 2 sockets on Stampede.
   There are 4 configurable and 2 fixed counter registers per PCU.  
   These routines only collect data on core_id 0 on each socket.

   There are 4 configure, 4 counter, 1 PCU global control, 
   and 2 fixed counter registers per PCU.

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
#include "cpuid.h"

/*! \name PCU global control register

   Layout in Table 2-74.  This register controls every
   non-fixed counter within a PCU.   It can freeze
   a PCU's control and counter registers.

   \note
   Documentation says they are 32 bit but only 64 bit
   works.
 */

#define CTL 0xC24

/*! \name PCU filter register

  Layout in Table 2-77.  Can filter events by
  Voltage/Frequency.
  
  ~~~
  Band 3             [31:24]
  Band 2             [23:16]
  Band 1             [15:8]
  Band 0             [7:9] 
  ~~~

 */
#define FILTER 0xC34

/*! \name PCU Performance Monitoring Registers
  
  Control register layout in 2-75.  These are used to select events.  There are
  4 per socket.
  ~~~
  occ_edge_det      [31]
  occ_invert        [30]
  threshhold        [28:24]
  invert threshold  [23]
  enable            [22]
  tid filter enable [19]
  edge detect       [18]
  clear counter     [17]
  occ_sel           [15:14]
  event select      [7:0]
  ~~~

  \note
  Documentation says they are 32 bit but only 64 bit
  works.

  Counter register layout in 2-76.  These are 64 bit but counters
  are only 48 bits wide.
  @{
*/
#define CTL0 0xC30
#define CTL1 0xC31
#define CTL2 0xC32
#define CTL3 0xC33

#define CTR0 0xC36
#define CTR1 0xC37
#define CTR2 0xC38
#define CTR3 0xC39
//@}

/*! \name Fixed registers

  Layout in Table 2-78 and 2-79.
  64 bits each.  Trace cycles in C6 or C3 state.
  @{
 */
#define FIXED_CTR0 0x3FC
#define FIXED_CTR1 0x3FD
//@}

/*! \brief KEYS will define the raw schema for this type. 
  
  The required order of registers is:
  -# Control registers in order
  -# Counter registers in order
  -# Fixed registers in order
*/
#define KEYS \
    X(CTL0,"C",""),	\
    X(CTL1,"C",""),	\
    X(CTL2,"C",""),	\
    X(CTL3,"C",""),	\
    X(CTR0,"E,W=48",""), \
    X(CTR1,"E,W=48",""), \
    X(CTR2,"E,W=48",""), \
    X(CTR3,"E,W=48",""), \
    X(FIXED_CTR0,"E,W=48",""), \
    X(FIXED_CTR1,"E,W=48","")

/*! \brief Filter 
  
  Can filter by frequency/voltage
 */
#define PCU_FILTER(...)	\
  ( (0x00ULL << 0) \
  | (0x00ULL << 8) \
  | (0x00ULL << 16) \
  | (0x00ULL << 24) \
  )

/*! \brief Event select
  
  Events are listed in Table 2-81.  They are defined in detail
  in Section 2.6.7.
  
  To change events to count:
  -# Define event below
  -# Modify events array in intel_snb_cbo_begin()
*/
#define PCU_PERF_EVENT(event)	\
  ( (event) \
  | (0ULL << 14) \
  | (0ULL << 17) \
  | (0ULL << 18) \
  | (1ULL << 22) \
  | (0ULL << 23) \
  | (1ULL << 24) \
  | (0ULL << 31) \
  )

/*! \name Events

  Events are listed in Table 2-81.  They are defined in detail
  in Section 2.6.7.

@{
 */
#define FREQ_MAX_OS_CYCLES      PCU_PERF_EVENT(0x06)
#define FREQ_MAX_CURRENT_CYCLES PCU_PERF_EVENT(0x07)
#define FREQ_MAX_TEMP_CYCLES    PCU_PERF_EVENT(0x04)
#define FREQ_MAX_POWER_CYCLES   PCU_PERF_EVENT(0x05)
#define FREQ_MIN_IO_CYCLES      PCU_PERF_EVENT(0x81)
#define FREQ_MIN_SNOOP_CYCLES   PCU_PERF_EVENT(0x82)
//@}

//! Configure and start counters for PCU
static int intel_snb_pcu_begin_socket(char *cpu, uint64_t *events, size_t nr_events)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t ctl;
  //uint64_t filter;


  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  ctl = 0x10102ULL; // enable freeze (bit 16), freeze (bit 8)
  if (pwrite(msr_fd, &ctl, sizeof(ctl), CTL) < 0) {
    ERROR("cannot enable freeze of PCU counters: %m\n");
    goto out;
  }

  /* Ignore PCU filter for now */
  /* The filters are part of event selection */
  /*
  filter = P_FILTER();
  if (pwrite(msr_fd, &filter, sizeof(filter), P_FILTER) < 0) {
    ERROR("cannot modify PCU filters: %m\n");
    goto out;
  }
  */

  /* Select Events for PCU */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", CTL0 + i, (unsigned long long) events[i]);
    if (pwrite(msr_fd, &events[i], sizeof(events[i]), CTL0 + i) < 0) { 
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n", 
            (unsigned long long) events[i],
            (unsigned) CTL0 + i,
            msr_path);
      goto out;
    }
  }
  
  ctl = 0x10000ULL; // unfreeze counter
  if (pwrite(msr_fd, &ctl, sizeof(ctl), CTL) < 0) {
    ERROR("cannot unfreeze PCU counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

//! Configure and start counters
static int intel_snb_pcu_begin(struct stats_type *type)
{
  int n_pmcs = 0;
  int nr = 0;
  uint64_t pcu_events[4] = {
    FREQ_MAX_TEMP_CYCLES,
    FREQ_MAX_POWER_CYCLES,
    FREQ_MIN_IO_CYCLES,
    FREQ_MIN_SNOOP_CYCLES
  };

  int i;
  if (signature(SANDYBRIDGE, &n_pmcs))
    for (i = 0; i < nr_cpus; i++) {
      char cpu[80];
      int pkg_id = -1;
      int core_id = -1;
      int smt_id = -1;
      int nr_cores = 0;
      snprintf(cpu, sizeof(cpu), "%d", i);      
      topology(cpu, &pkg_id, &core_id, &smt_id, &nr_cores);
      if (core_id == 0 && smt_id == 0)
	if (intel_snb_pcu_begin_socket(cpu, pcu_events,4) == 0)
	  nr++;
    }
  
  if (nr == 0)
    type->st_enabled = 0;

  return nr > 0 ? 0 : -1;
}

//! Collect values of counters for PCU
static void intel_snb_pcu_collect_socket(struct stats_type *type, char *cpu, int pkg_id)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;

  char pkg[80];
  snprintf(pkg, sizeof(pkg), "%d", pkg_id);

  TRACE("cpu %s pkg %s\n", cpu, pkg);

  stats = get_current_stats(type, pkg);
  if (stats == NULL)
    goto out;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

#define X(k,r...) \
  ({ \
    uint64_t val = 0; \
    if (pread(msr_fd, &val, sizeof(val), k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, k, msr_path); \
    else \
      stats_set(stats, #k, val); \
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

//! Collect values of counters
static void intel_snb_pcu_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    int pkg_id = -1;
    int core_id = -1;
    int smt_id = -1;
    int nr_cores = 0;
    snprintf(cpu, sizeof(cpu), "%d", i);
    topology(cpu, &pkg_id, &core_id, &smt_id, &nr_cores);
  
    if (core_id == 0 && smt_id == 0)
      intel_snb_pcu_collect_socket(type, cpu, pkg_id);
  }
}

//! Definition of stats for this type
struct stats_type intel_snb_pcu_stats_type = {
  .st_name = "intel_snb_pcu",
  .st_begin = &intel_snb_pcu_begin,
  .st_collect = &intel_snb_pcu_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
