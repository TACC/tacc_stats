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

// Sandy Bridge microarchitectures have signatures 06_2a and 06_2d with non-architectural events
// listed in Table 19-7, 19-8, and 19-9.  19-8 is 06_2a specific, 19-9 is 06_2d specific.  Stampede
// is 06_2d but no 06_2d specific events are used here.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// Uncore events are in this file.  Uncore events are found in the MSR and PCI config space.
// C-Box, PCU, and U-box counters are all in the MSR file
// This stuff is all in: 
//Intel Xeon Processor E5-2600 Product Family Uncore Performance Monitoring Guide

// Uncore MSR addresses
// Power Control Unit (PCU) 
/* Fixed Counters */
#define FIXED_CTR0 0x3FC
#define FIXED_CTR1 0x3FD
/* Counter Config Registers */
#define CTL0 0xC30
#define CTL1 0xC31
#define CTL2 0xC32
#define CTL3 0xC33
/* Counter Filters */
#define FILTER 0xC34
/* Box Control */
#define CTL 0xC24
/* Counter Registers */
#define CTR0 0xC36
#define CTR1 0xC37
#define CTR2 0xC38
#define CTR3 0xC39

// Width of 48 for PCU 
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

/* Defs in Table 2-77 */
/* Event filters in PCU
Band 3             [31:24]
Band 2             [23:16]
Band 1             [15:8]
Band 0             [7:0]
*/

#define PCU_FILTER(...)	\
  ( (0x00ULL << 0) \
  | (0x00ULL << 8) \
  | (0x00ULL << 16) \
  | (0x00ULL << 24) \
  )

/* Events in PCU
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
*/

/* Defs in Table 2-75 */
#define PCU_PERF_EVENT(event)	\
  ( (event) \
  | (0ULL << 14) /* Select which occupancy counter to use - C0: 01 C3: 10 C6: 11 */ \
  | (0ULL << 17) /* Reset Counters. */ \
  | (0ULL << 18) /* Edge Detection. */ \
  | (1ULL << 22) /* Enable. */ \
  | (0ULL << 23) /* Invert */ \
  | (1ULL << 24) /* Threshold */ \
  | (0ULL << 31) /* Enables edges foc occupancy */ \
  )

/* Definitions in Table 2-14 */
/* Advice in Table 2-80 */
#define FREQ_MAX_OS_CYCLES      PCU_PERF_EVENT(0x06)
#define FREQ_MAX_CURRENT_CYCLES PCU_PERF_EVENT(0x07)
#define FREQ_MAX_TEMP_CYCLES    PCU_PERF_EVENT(0x04)
#define FREQ_MAX_POWER_CYCLES   PCU_PERF_EVENT(0x05)
#define FREQ_MIN_IO_CYCLES      PCU_PERF_EVENT(0x81) /* Extra select bit */
#define FREQ_MIN_SNOOP_CYCLES   PCU_PERF_EVENT(0x82) /* Extra select bit */

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

static int intel_snb_pcu_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t pcu_events[4] = {FREQ_MAX_TEMP_CYCLES,
			    FREQ_MAX_POWER_CYCLES,
			    FREQ_MIN_IO_CYCLES,
			    FREQ_MIN_SNOOP_CYCLES};


  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];
    int core_id = -1;
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
	if (intel_snb_pcu_begin_socket(cpu, pcu_events,4) == 0)
	  nr++; /* HARD */
      }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_pcu_collect_socket(struct stats_type *type, char *cpu, char* pcu)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;

  stats = get_current_stats(type, pcu);
  if (stats == NULL)
    goto out;

  TRACE("cpu %s\n", cpu);
  TRACE("cpu %s\n", pcu);

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

static void intel_snb_pcu_collect(struct stats_type *type)
{
  // CPUs 0 and 8 have core_id 0 on Stampede at least

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];
    int core_id = -1;

    char socket[80];
    char socket_id_path[80];
    int socket_id = -1;

    char pcu[80];

    /* Only collect uncore counters on core 0 of a socket. */
    snprintf(core_id_path, sizeof(core_id_path), 
	     "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path); /* errno */
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
	snprintf(pcu, sizeof(pcu), "%d", socket_id);
	intel_snb_pcu_collect_socket(type, cpu, pcu);
      }
  }
}

struct stats_type intel_snb_pcu_stats_type = {
  .st_name = "intel_snb_pcu",
  .st_begin = &intel_snb_pcu_begin,
  .st_collect = &intel_snb_pcu_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
