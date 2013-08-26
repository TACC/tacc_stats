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
// C-Box control and counter registers 
// 8 C-Boxes, 4 counters each.  Each counter has a different restriction on what it counts.
/* Box Control */
#define C_CTL0 0xD04
#define C_CTL1 0xD24
#define C_CTL2 0xD44
#define C_CTL3 0xD64
#define C_CTL4 0xD84
#define C_CTL5 0xDA4
#define C_CTL6 0xDC4
#define C_CTL7 0xDE4
/* Counter Filters */
#define C_FILTER0 0xD14
#define C_FILTER1 0xD34
#define C_FILTER2 0xD54
#define C_FILTER3 0xD74
#define C_FILTER4 0xD94
#define C_FILTER5 0xDB4
#define C_FILTER6 0xDD4
#define C_FILTER7 0xDF4
/* Counter Config Registers 32 bit */
#define C_CTL0_0 0xD10
#define C_CTL0_1 0xD11
#define C_CTL0_2 0xD12
#define C_CTL0_3 0xD13

#define C_CTL1_0 0xD30
#define C_CTL1_1 0xD31
#define C_CTL1_2 0xD32
#define C_CTL1_3 0xD33

#define C_CTL2_0 0xD50
#define C_CTL2_1 0xD51
#define C_CTL2_2 0xD52
#define C_CTL2_3 0xD53

#define C_CTL3_0 0xD70
#define C_CTL3_1 0xD71
#define C_CTL3_2 0xD72
#define C_CTL3_3 0xD73

#define C_CTL4_0 0xD90
#define C_CTL4_1 0xD91
#define C_CTL4_2 0xD92
#define C_CTL4_3 0xD93

#define C_CTL5_0 0xDB0
#define C_CTL5_1 0xDB1
#define C_CTL5_2 0xDB2
#define C_CTL5_3 0xDB3

#define C_CTL6_0 0xDD0
#define C_CTL6_1 0xDD1
#define C_CTL6_2 0xDD2
#define C_CTL6_3 0xDD3

#define C_CTL7_0 0xDF0
#define C_CTL7_1 0xDF1
#define C_CTL7_2 0xDF2
#define C_CTL7_3 0xDF3
/* Counter Registers 64 bit but only 44 bit for counting */
#define C_CTR0_0 0xD16
#define C_CTR0_1 0xD17
#define C_CTR0_2 0xD18
#define C_CTR0_3 0xD19

#define C_CTR1_0 0xD36
#define C_CTR1_1 0xD37
#define C_CTR1_2 0xD38
#define C_CTR1_3 0xD39

#define C_CTR2_0 0xD56
#define C_CTR2_1 0xD57
#define C_CTR2_2 0xD58
#define C_CTR2_3 0xD59

#define C_CTR3_0 0xD76
#define C_CTR3_1 0xD77
#define C_CTR3_2 0xD78
#define C_CTR3_3 0xD79

#define C_CTR4_0 0xD96
#define C_CTR4_1 0xD97
#define C_CTR4_2 0xD98
#define C_CTR4_3 0xD99

#define C_CTR5_0 0xDB6
#define C_CTR5_1 0xDB7
#define C_CTR5_2 0xDB8
#define C_CTR5_3 0xDB9

#define C_CTR6_0 0xDD6
#define C_CTR6_1 0xDD7
#define C_CTR6_2 0xDD8
#define C_CTR6_3 0xDD9

#define C_CTR7_0 0xDF6
#define C_CTR7_1 0xDF7
#define C_CTR7_2 0xDF8
#define C_CTR7_3 0xDF9

// Power Control Unit (PCU) 
/* Fixed Counters */
#define PCU_FIXED_CTR0 0x3FC
#define PCU_FIXED_CTR1 0x3FD
/* Counter Config Registers */
#define PCU_CTL0 0xC30
#define PCU_CTL1 0xC31
#define PCU_CTL2 0xC32
#define PCU_CTL3 0xC33
/* Counter Filters */
#define PCU_FILTER0 0xC34
/* Box Control */
#define PCU_CTL0 0xC24
/* Counter Registers */
#define PCU_CTR0 0xC36
#define PCU_CTR1 0xC37
#define PCU_CTR2 0xC38
#define PCU_CTR3 0xC39

// Width of 44 for C-Boxes
#define KEYS \
    X(FIXED_CTR0, "E,W=44", ""), \
    X(FIXED_CTR1, "E,W=44", ""), \
    X(FIXED_CTR2, "E,W=44", ""), \
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
    X(CTR7, "E,W=48", "")

/* Shouldn't need these in stats file,
all counters are always on, and ovf is handled 
in post processing. fixed counters are fixed :)
, \
  X(FIXED_CTR_CTRL, FIXED_CTL, "C", ""), \
  X(PERF_GLOBAL_STATUS, "C", ""), \
  X(PERF_GLOBAL_CTRL, "C", ""), \
  X(PERF_GLOBAL_OVF_CTRL, "C", "")
*/

static void get_cpuid_signature(int cpuid_file, char* signature)
{
  int ebx = 0, ecx = 0, edx = 0, eax = 1;
  __asm__ ("cpuid": "=b" (ebx), "=c" (ecx), "=d" (edx), "=a" (eax):"a" (eax));

  int model = (eax & 0x0FF) >> 4;
  int extended_model = (eax & 0xF0000) >> 12;
  int family_code = (eax & 0xF00) >> 8;
  int extended_family_code = (eax & 0xFF00000) >> 16;

  snprintf(signature,sizeof(signature),"%02x_%x", extended_family_code | family_code, extended_model | model);

}
static int cpu_is_sandybridge(char *cpu)
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
  
  get_cpuid_signature(cpuid_fd,signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_2a", 5) !=0 && strncmp(signature, "06_2d", 5) !=0)
    goto out;


  // This check isn't really necessary since SNB is always perf vers 3
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

static int intel_snb_uncore_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
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

  /* Enable counters globally, 8 PMC and 3 fixed. */
  global_ctr_ctrl = 0xFF | (0x7ULL << 32);
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

/* Non-architectural Perfomance Events */
/* From Table 19-7 Sandy Bridge Microarchitecture 06_2A and 06_2D */
/* Stampede has 06_2D and can also use Table 19-9 */
#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x20)
#define SSE_DOUBLE_SCALAR_PACKED       PERF_EVENT(0x10, 0x90)
#define SIMD_FP_256_PACKED_DOUBLE      PERF_EVENT(0x11, 0x02)
/* L1 CACHE */
#define L1D_REPLACEMENT                PERF_EVENT(0x51, 0x01) 
/* Stalls */
#define RESOURCE_STALLS_ANY            PERF_EVENT(0xA2, 0x01) 
/* Floating Point */
/* Load ops */
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0xD0, 0x81) /* PMC0-3 only */
/* Load hits */
#define MEM_LOAD_UOPS_RETIRED_L1_HIT   PERF_EVENT(0xD1, 0x01) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_L2_HIT   PERF_EVENT(0xD1, 0x02) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_LLC_HIT  PERF_EVENT(0xD1, 0x04) /* PMC0-3 only */
/* Other Misses */
#define MEM_LOAD_UOPS_RETIRED_LLC_MISS PERF_EVENT(0xD1, 0x20) /* PMC0-3 only */
#define MEM_LOAD_UOPS_RETIRED_HIT_LFB  PERF_EVENT(0xD1, 0x40) /* PMC0-3 only */

static int intel_snb_uncore_begin(struct stats_type *type)
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
      if (intel_snb_uncore_begin_cpu(cpu, events, 8) == 0)
	nr++; /* HARD */
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_uncore_collect_cpu(struct stats_type *type, char *cpu)
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

static void intel_snb_uncore_collect(struct stats_type *type)
{
  // CPUs 0 and 8 have core_id 0 on Stampede at least

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];
    int core_id = -1;

    /* Only collect uncore counters on core 0 of a socket. */
    snprintf(core_id_path, sizeof(core_id_path), "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path); /* errno */
      continue;
    }

    if (core_id != 0)
      continue;

    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_sandybridge(cpu))
      intel_snb_uncore_collect_cpu(type, cpu);
  }
}

struct stats_type intel_snb_uncore_stats_type = {
  .st_name = "intel_snb",
  .st_begin = &intel_snb_uncore_begin,
  .st_collect = &intel_snb_uncore_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
