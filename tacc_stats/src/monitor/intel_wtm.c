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
#include "cpuid.h"

// Westmere microarchitectures have signature 06_25,06_2c,06_1f with non-architectural events
// listed in Table 19-11.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// IA32_PMCx MSRs start at address 0C1H and occupy a contiguous block of MSR
// address space; the number of MSRs per logical processor is reported using
// CPUID.0AH:EAX[15:8].

// IA32_PERFEVTSELx MSRs start at address 186H and occupy a contiguous block
// of MSR address space. Each performance event select register is paired with a
// corresponding performance counter in the 0C1H address block.

#define IA32_CTR0 0xC1 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_CTR1 0xC2 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_CTR2 0xC3 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_CTR3 0xC4 /* CPUID.0AH: EAX[15:8] > 3 */

#define IA32_CTL0 0x186 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_CTL1 0x187 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_CTL2 0x188 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_CTL3 0x189 /* CPUID.0AH: EAX[15:8] > 3 */

// IA32_PERFEVTSELx MSR layout
//   [0, 7] Event Select
//   [8, 15] Unit Mask (UMASK)
//   16 USR
//   17 OS
//   18 E Edge_detect
//   19 PC Pin control
//   20 INT APIC interrupt enable
//   21 ANY Any thread (version 3)
//   22 EN Enable counters
//   23 INV Invert counter mask
//   [24, 31] Counter Mask (CMASK)
//   [32, 63] Reserved

#define IA32_FIXED_CTR0 0x309 /* Instr_Retired.Any, CPUID.0AH: EDX[4:0] > 0 */
#define IA32_FIXED_CTR1 0x30A /* CPU_CLK_Unhalted.Core, CPUID.0AH: EDX[4:0] > 1 */
#define IA32_FIXED_CTR2 0x30B /* CPU_CLK_Unhalted.Ref, CPUID.0AH: EDX[4:0] > 2 */
#define IA32_FIXED_CTR_CTRL 0x38D /* CPUID.0AH: EAX[7:0] > 1 */
#define IA32_PERF_GLOBAL_STATUS 0x38E
#define IA32_PERF_GLOBAL_CTRL 0x38F
#define IA32_PERF_GLOBAL_OVF_CTRL 0x390

#define KEYS \
  X(FIXED_CTR0, "E,W=48", ""), \
  X(FIXED_CTR1, "E,W=48", ""), \
  X(FIXED_CTR2, "E,W=48", ""), \
  X(CTL0, "C", ""), \
  X(CTL1, "C", ""), \
  X(CTL2, "C", ""), \
  X(CTL3, "C", ""), \
  X(CTR0, "E,W=48", ""), \
  X(CTR1, "E,W=48", ""), \
  X(CTR2, "E,W=48", ""), \
  X(CTR3, "E,W=48", "")

 /* Shouldn't need these in stats file,                                        
all counters are always on, and ovf is handled                                 
in post processing                                                             
  , \        
  X(FIXED_CTR_CTRL, "C", ""), \
  X(PERF_GLOBAL_STATUS, "C", ""), \
  X(PERF_GLOBAL_CTRL, "C", ""), \
  X(PERF_GLOBAL_OVF_CTRL, "C", "")
*/

  /*
    EAX[31:24] Number of arch events supported per logical processor
    EAX[23:16] Number of bits per programmable counter (width)
    EAX[15:8] Number of counters per logical processor
    EAX[7:0] Architectural PerfMon Version

    EBX[31:7] Reserved
    EBX[6] Branch Mispredicts Retired; 0 = supported
    EBX[5] Branch Instructions Retired; 0 = supported
    EBX[4] Last Level Cache Misses; 0 = supported
    EBX[3] Last Level Cache References; 0 = supported
    EBX[2] Reference Cycles; 0 = supported
    EBX[1] Instructions Retired; 0 = supported
    EBX[0] Core Cycles; 0 = supported

    ECX[31:0] Reserved

    EDX[31:13] Reserved
    EDX[12:5] Number of Bits in the Fixed Counters (width)
    EDX[4:0] Number of Fixed Counters
  */

static int intel_wtm_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
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
  global_ctr_ctrl = 0;
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
  rc = 0;

  /* Enable fixed counters.  Three 4 bit blocks, enable OS, User, Any thread. */
  fixed_ctr_ctrl = 0x777;
  if (pwrite(msr_fd, &fixed_ctr_ctrl, sizeof(fixed_ctr_ctrl), IA32_FIXED_CTR_CTRL) < 0)
    ERROR("cannot enable fixed counters: %m\n");

  /* Enable counters globally, 4 PMC and 3 fixed. */
  global_ctr_ctrl = 0xF | (0x7ULL << 32);
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0)
    ERROR("cannot enable performance counters: %m\n");

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

#define PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (1ULL << 16) /* Count in user mode (CPL == 0). */ \
  | (1ULL << 17) /* Count in OS mode (CPL > 0). */ \
  | (1ULL << 21) /* Any thread. */ \
  | (1ULL << 22) /* Enable. */ \
  )

#define MEM_UNCORE_RETIRED_REMOTE_DRAM PERF_EVENT(0x0F, 0x10) /* CHECKME */
#define MEM_UNCORE_RETIRED_LOCAL_DRAM  PERF_EVENT(0x0F, 0x20) /* CHECKME */
#define FP_COMP_OPS_EXE_X87            PERF_EVENT(0x10, 0x01)
#define MEM_LOAD_RETIRED_L1D_HIT       PERF_EVENT(0xCB, 0x01)
#define MEM_LOAD_RETIRED_L2_HIT        PERF_EVENT(0xCB, 0x02)
#define MEM_LOAD_RETIRED_L3_HIT        PERF_EVENT(0xCB, 0x0C)
#define MEM_LOAD_RETIRED_L3_MISS       PERF_EVENT(0xCB, 0x10) /* May be same as 0x0F/0x10 + 0x0F/0x20. */

#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x20)

static int intel_wtm_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t events[] = {
    MEM_UNCORE_RETIRED_REMOTE_DRAM,
    MEM_UNCORE_RETIRED_LOCAL_DRAM,
    FP_COMP_OPS_EXE_SSE_FP_PACKED,
    FP_COMP_OPS_EXE_SSE_FP_SCALAR,
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    int nr_events = 0;
    snprintf(cpu, sizeof(cpu), "%d", i);
    if (signature(WESTMERE, cpu, &nr_events))
      if (intel_wtm_begin_cpu(cpu, events, nr_events) == 0)
	nr++;
  }

  if (nr == 0) 
    type->st_enabled = 0;
  return nr > 0 ? 0 : -1;
}

static void intel_wtm_collect_cpu(struct stats_type *type, char *cpu)
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

static void intel_wtm_collect(struct stats_type *type)
{
  int i;

  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    int nr_events = 0;
    snprintf(cpu, sizeof(cpu), "%d", i);
    if (signature(WESTMERE, cpu, &nr_events))
      intel_wtm_collect_cpu(type, cpu);
  }
}

struct stats_type intel_wtm_stats_type = {
  .st_name = "intel_wtm",
  .st_begin = &intel_wtm_begin,
  .st_collect = &intel_wtm_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};

/*  LocalWords:  EAX
 */
