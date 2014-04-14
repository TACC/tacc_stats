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

static void get_cpuid_signature(int cpuid_file, char* signature, size_t sigbuflen)
{
  int ebx = 0, ecx = 0, edx = 0, eax = 1;
  __asm__ ("cpuid": "=b" (ebx), "=c" (ecx), "=d" (edx), "=a" (eax):"a" (eax));

  int model = (eax & 0x0FF) >> 4;
  int extended_model = (eax & 0xF0000) >> 12;
  int family_code = (eax & 0xF00) >> 8;
  int extended_family_code = (eax & 0xFF00000) >> 16;

  snprintf(signature,sigbuflen,"%02x_%x", extended_family_code | family_code, extended_model | model);

}
static int cpu_is_westmere(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;
  char signature[5];

  /* Open /dev/cpuid/cpu/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }
  
  /* Get cpu vendor. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }

  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  TRACE("cpu %s, vendor `%.12s'\n", cpu, (char*) buf + 4);

  if (strncmp((char*) buf + 4, "GenuineIntel", 12) != 0)
    goto out; /* CentaurHauls? */

  if (pread(cpuid_fd, buf, sizeof(buf), 0x0A) < 0) {
    ERROR("cannot read `%s': %m\n", cpuid_path);
    goto out;
  }

  TRACE("cpu %s, buf %08x %08x %08x %08x\n", cpu, buf[0], buf[1], buf[2], buf[3]);

  get_cpuid_signature(cpuid_fd,signature,sizeof(signature));
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_25", 5) !=0 && strncmp(signature, "06_2c", 5) !=0  && strncmp(signature, "06_1f", 5) !=0)
    goto out;



  int perf_ver = buf[0] & 0xff;
  TRACE("cpu %s, perf_ver %d\n", cpu, perf_ver);
  switch (perf_ver) {
  default:
    ERROR("unknown perf monitoring version %d\n", perf_ver);
    goto out;
  case 0:
    goto out;
  case 1:
    goto out;
  case 2:
    /* Adds IA32_PERF_GLOBAL_CTRL, IA32_PERF_GLOBAL_STATUS,
       IA32_PERF_GLOBAL_CTRL. */
    goto out;
  case 3:
    /* Close enough. */
    rc = 1;
    break;
  }

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

#ifdef DEBUG
  int nr_ctrs = (buf[0] >> 8) & 0xFF;
  int ctr_width = (buf[0] >> 16) & 0xFF;

  int nr_fixed_ctrs = buf[3] & 0x1F;
  int fixed_ctr_width = (buf[3] >> 5) & 0xFF;

  TRACE("nr_ctrs %d, ctr_width %d, nr_fixed_ctrs %d, fixed_ctr_width %d\n",
        nr_ctrs, ctr_width, nr_fixed_ctrs, fixed_ctr_width);
#endif

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

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
    FP_COMP_OPS_EXE_X87,
    MEM_LOAD_RETIRED_L1D_HIT,
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_westmere(cpu))
      if (intel_wtm_begin_cpu(cpu, events, 4) == 0)
	nr++; /* HARD */
  }

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
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_westmere(cpu))
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
