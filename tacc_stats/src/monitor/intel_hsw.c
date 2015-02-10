/*! 
 \file intel_hsw.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Haswell Processors


  \par Details such as Tables and Figures can be found in:
  "Intel® 64 and IA-32 Architectures Software Developer’s Manual
  Volume 3B: System Programming Guide, Part 2" 
  Order Number: 325384 January 2015 \n

  \note
  Haswell microarchitectures have signatures 06_3c, 06_45, 06_46, 06_47 and EP 06_3f. 
  Non-architectural events are listed in Table 19-7, 19-8, and 19-9.  
  Table 19-8 is 06_2a specific, Table 19-9 is 06_2d specific.  


  \par Location of cpu info and monitoring register files:

  ex) Display cpuid and msr file for cpu 0:

      $ ls -l /dev/cpu/0
      total 0
      crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
      crw-------  1 root root 202, 0 Oct 28 18:47 msr


  \par MSR address layout of registers:

  There are 20 logical processors on a Haswell EP E52660v3 with Hyperthreading disabled.
  There are 8 configurable and 3 fixed counter registers per processor.

  IA32_PMCx (CTRx) MSRs start at address 0C1H and occupy a contiguous block of MSR
  address space; the number of MSRs per logical processor is reported using
  CPUID.0AH:EAX[15:8].  

  IA32_PERFEVTSELx (CTLx) MSRs start at address 186H and occupy a contiguous block
  of MSR address space. Each performance event select register is paired with a
  corresponding performance counter in the 0C1H address block.
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
#include "cpu_is_hsw.h"

//@{
/*! \name Configurable Performance Monitoring Registers

  Control register layout shown in Fig 18-36.
  These are used to select events and ways to count events.
  ~~~
  [0, 7] Event Select       : Choose Event
  [8, 15] Unit Mask (UMASK) : Choose Subevent
  16 USR                    : Count when in user mode
  17 OS                     : Count when in root mode
  18 E Edge_detect          : Can measure time spent in state
  19 PC Pin control         : Ovrflow control
  20 INT APIC               : Ovrflow control
  21 ANY                    : Counts events from any thread on core
  22 EN                     : Enables counters
  23 INV                    : Inverts Counter Mask
  [24, 31] Counter Mask     : Counts in a cycle must exceed CMASK if set
  [32] IN_TX                : In Trans. Rgn
  [33] IN_TXCP              : In Tx exclude abort
  [34, 63] Reserved
  ~~~  

  Counter registers are 64 bit but 48 bits wide.  These
  are configured by the control registers and 
  hold the counter values.
*/

#define IA32_CTL0 0x186
#define IA32_CTL1 0x187
#define IA32_CTL2 0x188
#define IA32_CTL3 0x189
#define IA32_CTL4 0x18A
#define IA32_CTL5 0x18B
#define IA32_CTL6 0x18C
#define IA32_CTL7 0x18D

#define IA32_CTR0 0xC1
#define IA32_CTR1 0xC2
#define IA32_CTR2 0xC3
#define IA32_CTR3 0xC4
#define IA32_CTR4 0xC5
#define IA32_CTR5 0xC6
#define IA32_CTR6 0xC7
#define IA32_CTR7 0xC8
//@}

/*! \name Fixed Counter Registers

  These counters always count the same events.  Fig 18-7 describes
  how to enable these registers.  Events are described on page 18-10.
  @{
*/
#define IA32_FIXED_CTR_CTRL 0x38D //!< Fixed Counter Control Register
#define IA32_FIXED_CTR0     0x309 //!< Fixed Counter 0: Instructions Retired
#define IA32_FIXED_CTR1     0x30A //!< Fixed Counter 1: Core Clock Cycles
#define IA32_FIXED_CTR2     0x30B //!< Fixed Counter 2: Reference Clock Cycles
//@}

/*! \name Global Control Registers
  
  Layout in Fig 18-8 and 18-9.  Controls for all
  registers.
  @{
*/
#define IA32_PERF_GLOBAL_STATUS   0x38E //!< indicates overflow 
#define IA32_PERF_GLOBAL_CTRL     0x38F //!< enables all fixed and configurable counters  
#define IA32_PERF_GLOBAL_OVF_CTRL 0x390 //!< clears overflow indicators in GLOBAL_STATUS.
//@}

/*! \brief KEYS will define the raw schema for this type

  The required order of registers is:
  -# Control registers in order
  -# Counter registers in order
  -# Fixed registers in order

  All counter registers are 48 bits wide.
 */
#define KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", ""), \
    X(CTL4, "C", ""), \
    X(CTL5, "C", ""), \
    X(CTL6, "C", ""), \
    X(CTL7, "C", ""), \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", ""), \
    X(CTR4, "E,W=48", ""), \
    X(CTR5, "E,W=48", ""), \
    X(CTR6, "E,W=48", ""), \
    X(CTR7, "E,W=48", ""), \
    X(FIXED_CTR0, "E,W=48", ""), \
    X(FIXED_CTR1, "E,W=48", ""), \
    X(FIXED_CTR2, "E,W=48", "")

/*! \brief Event select 

  Non-architectural events are listed and defined in 
  Table 19-7, 19-8, and 19-9.  Table 19-8 is 06_2a specific, 
  Table 19-9 is 06_2d specific.  

  To change events to count:
  -# Define event below
  -# Modify events array in intel_hsw_begin()
*/
#define PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (1ULL << 16) \
  | (1ULL << 17) \
  | (1ULL << 21) \
  | (1ULL << 22) \
  )

/*! \name Events 

  Non-architectural events are listed in Table 19-7, 19-8, and 19-9. 
  Table 19-8 is 06_2a specific, Table 19-9 is 06_2d specific.

  @{
*/
#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x80)
#define SSE_DOUBLE_SCALAR_PACKED       PERF_EVENT(0x10, 0x90)
#define SIMD_FP_256_PACKED_DOUBLE      PERF_EVENT(0x11, 0x02)
#define L1D_REPLACEMENT                PERF_EVENT(0x51, 0x01) 
#define RESOURCE_STALLS_ANY            PERF_EVENT(0xA2, 0x01) 
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0xD0, 0x81) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_L1_HIT   PERF_EVENT(0xD1, 0x01) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_L2_HIT   PERF_EVENT(0xD1, 0x02) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_LLC_HIT  PERF_EVENT(0xD1, 0x04) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_LLC_MISS PERF_EVENT(0xD1, 0x20) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_HIT_LFB  PERF_EVENT(0xD1, 0x40) // CTR0-3 Only
//@}


//! Configure and start counters for a cpu
static int intel_hsw_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t global_ctr_ctrl, fixed_ctr_ctrl;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  /* Disable counters globally. */
  global_ctr_ctrl = 0x0ULL;
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0) {
    ERROR("cannot disable performance counters: %m\n");
    goto out;
  }

  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", IA32_CTL0 + i, (unsigned long long) events[i]);
    if (pwrite(msr_fd, &events[i], sizeof(events[i]), IA32_CTL0 + i) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) events[i],
            (unsigned) IA32_CTL0 + i,
            msr_path);
      goto out;
    }
  }

  /* Reset all the counters */
  uint64_t zero = 0x0ULL;
  for (i = 0; i < nr_events; i++) {
    if (pwrite(msr_fd, &zero, sizeof(zero), IA32_CTR0 + i) < 0) {
      ERROR("cannot reset counter %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) zero,
            (unsigned) IA32_CTR0 + i,
            msr_path);
      goto out;
    }
  }
  if (pwrite(msr_fd, &zero, sizeof(zero), IA32_FIXED_CTR0) < 0 ||
      pwrite(msr_fd, &zero, sizeof(zero), IA32_FIXED_CTR1) < 0 || 
      pwrite(msr_fd, &zero, sizeof(zero), IA32_FIXED_CTR2) < 0) {
    ERROR("cannot reset counter %016llX to MSRs (%08X,%08X,%08X) through `%s': %m\n",
	  (unsigned long long) zero,
	  (unsigned) IA32_FIXED_CTR0,
	  (unsigned) IA32_FIXED_CTR1,
	  (unsigned) IA32_FIXED_CTR2,
	  msr_path);
      goto out;
  }
  
  rc = 0;

  /* Enable fixed counters.  Three 4 bit blocks, enable OS, User, Any thread. */
  fixed_ctr_ctrl = 0x777UL;
  if (pwrite(msr_fd, &fixed_ctr_ctrl, sizeof(fixed_ctr_ctrl), IA32_FIXED_CTR_CTRL) < 0)
    ERROR("cannot enable fixed counters: %m\n");

  /* Enable counters globally, 8 PMC and 3 fixed. */
  global_ctr_ctrl = 0xFF | (0x7ULL << 32);
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0)
    ERROR("cannot enable performance counters: %m\n");

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

//! Configure and start counters
static int intel_hsw_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t events[] = {
    MEM_UOPS_RETIRED_ALL_LOADS,
    MEM_LOAD_UOPS_RETIRED_L1_HIT,
    MEM_LOAD_UOPS_RETIRED_L2_HIT,
    MEM_LOAD_UOPS_RETIRED_LLC_HIT,
    L1D_REPLACEMENT,
    FP_COMP_OPS_EXE_SSE_FP_SCALAR,
    FP_COMP_OPS_EXE_SSE_FP_PACKED,
    SIMD_FP_256_PACKED_DOUBLE,
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_haswell(cpu))
      if (intel_hsw_begin_cpu(cpu, events, 8) == 0)
	nr++;
  }

  return nr > 0 ? 0 : -1;
}

//! Collect values in counters for cpu
static void intel_hsw_collect_cpu(struct stats_type *type, char *cpu)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;

  stats = get_current_stats(type, cpu);
  if (stats == NULL)
    goto out;

  TRACE("cpu %s\n", cpu);

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }
  
#define X(k,r...) \
  ({ \
    uint64_t val = 0; \
    if (pread(msr_fd, &val, sizeof(val), IA32_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, IA32_##k, msr_path); \
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
static void intel_hsw_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_haswell(cpu))
      intel_hsw_collect_cpu(type, cpu);
  }
}

//! Definition of stats entry for this type
struct stats_type intel_hsw_stats_type = {
  .st_name = "intel_hsw",
  .st_begin = &intel_hsw_begin,
  .st_collect = &intel_hsw_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
