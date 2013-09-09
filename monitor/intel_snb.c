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
#include "cpu_is_snb.h"

// Sandy Bridge microarchitectures have signatures 06_2a and 06_2d with non-architectural events
// listed in Table 19-7, 19-8, and 19-9.  19-8 is 06_2a specific, 19-9 is 06_2d specific.  Stampede
// is 06_2d but no 06_2d specific events are used here.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

/* Info about this stuff can be found in 
Intel® 64 and IA-32 Architectures Software Developer’s Manual
Volume 3B: System Programming Guide, Part 2
 */

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
#define IA32_CTR4 0xC5 /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTR5 0xC6 /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTR6 0xC7 /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTR7 0xC8 /* CPUID.0AH: EAX[15:8] = 8 */

#define IA32_CTL0 0x186 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_CTL1 0x187 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_CTL2 0x188 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_CTL3 0x189 /* CPUID.0AH: EAX[15:8] > 3 */
#define IA32_CTL4 0x18A /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTL5 0x18B /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTL6 0x18C /* CPUID.0AH: EAX[15:8] = 8 */
#define IA32_CTL7 0x18D /* CPUID.0AH: EAX[15:8] = 8 */

#define IA32_FIXED_CTR0           0x309 /* Instr_Retired.Any, CPUID.0AH: EDX[4:0] > 0 */
#define IA32_FIXED_CTR1           0x30A /* CPU_CLK_Unhalted.Core, CPUID.0AH: EDX[4:0] > 1 */
#define IA32_FIXED_CTR2           0x30B /* CPU_CLK_Unhalted.Ref, CPUID.0AH: EDX[4:0] > 2 */
#define IA32_FIXED_CTR_CTRL       0x38D /* CPUID.0AH: EAX[7:0] > 1 Fig 18-7 */
#define IA32_PERF_GLOBAL_STATUS   0x38E /* Indicates counter ovf Fig 18-9 */
#define IA32_PERF_GLOBAL_CTRL     0x38F /* Enables counters Fig 18-8 */
#define IA32_PERF_GLOBAL_OVF_CTRL 0x390 /* Controls counter ovf Fig 18-9 */

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


/* Fig 18-6 */
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

#define PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (1ULL << 16) /* Count in user mode (CPL == 0). */ \
  | (1ULL << 17) /* Count in OS mode (CPL > 0). */ \
  | (1ULL << 21) /* Any thread. */ \
  | (1ULL << 22) /* Enable. */ \
  )

/* Non-architectural Perfomance Events */
/* From Table 19-7 Sandy Bridge Microarchitecture 06_2A and 06_2D */
/* Stampede has 06_2D and can also use Table 19-9 */

#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x20)
#define SSE_DOUBLE_SCALAR_PACKED       PERF_EVENT(0x10, 0x90)
#define SIMD_FP_256_PACKED_DOUBLE      PERF_EVENT(0x11, 0x02)
#define L1D_REPLACEMENT                PERF_EVENT(0x51, 0x01) 
#define RESOURCE_STALLS_ANY            PERF_EVENT(0xA2, 0x01) 
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0xD0, 0x81) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_L1_HIT   PERF_EVENT(0xD1, 0x01) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_L2_HIT   PERF_EVENT(0xD1, 0x02) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_LLC_HIT  PERF_EVENT(0xD1, 0x04) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_LLC_MISS PERF_EVENT(0xD1, 0x20) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_HIT_LFB  PERF_EVENT(0xD1, 0x40) /* PMC0-3 only */

static int intel_snb_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
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

static int intel_snb_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t events[] = {
    MEM_UOPS_RETIRED_ALL_LOADS,
    MEM_LOAD_UOPS_RETIRED_L1_HIT,
    MEM_LOAD_UOPS_RETIRED_L2_HIT,
    MEM_LOAD_UOPS_RETIRED_LLC_HIT,
    SSE_DOUBLE_SCALAR_PACKED,
    SIMD_FP_256_PACKED_DOUBLE,
    L1D_REPLACEMENT,
    RESOURCE_STALLS_ANY,
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_sandybridge(cpu))
      if (intel_snb_begin_cpu(cpu, events, 8) == 0)
	nr++; /* HARD */
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_collect_cpu(struct stats_type *type, char *cpu)
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

static void intel_snb_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_sandybridge(cpu))
      intel_snb_collect_cpu(type, cpu);
  }
}

struct stats_type intel_snb_stats_type = {
  .st_name = "intel_snb",
  .st_begin = &intel_snb_begin,
  .st_collect = &intel_snb_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
