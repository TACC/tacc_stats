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

#define IA32_PMC0 0xC1 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_PMC1 0xC2 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_PMC2 0xC3 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_PMC3 0xC4 /* CPUID.0AH: EAX[15:8] > 3 */

#define IA32_PERFEVTSEL0 0x186 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_PERFEVTSEL1 0x187 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_PERFEVTSEL2 0x188 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_PERFEVTSEL3 0x189 /* CPUID.0AH: EAX[15:8] > 3 */

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
  X(PMC0, "event", ""), \
  X(PMC1, "event", ""), \
  X(PMC2, "event", ""), \
  X(PMC3, "event", ""), \
  X(PERFEVTSEL0, "", ""), \
  X(PERFEVTSEL1, "", ""), \
  X(PERFEVTSEL2, "", ""), \
  X(PERFEVTSEL3, "", ""), \
  X(FIXED_CTR0, "event", ""), \
  X(FIXED_CTR1, "event", ""), \
  X(FIXED_CTR2, "event", ""), \
  X(FIXED_CTR_CTRL, "", ""), \
  X(PERF_GLOBAL_STATUS, "", ""), \
  X(PERF_GLOBAL_CTRL, "", ""), \
  X(PERF_GLOBAL_OVF_CTRL, "", "")

static int cpu_is_nehalem(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;

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

  int perf_ver = buf[0] & 0xff;
  TRACE("cpu %s, perf_ver %d\n", cpu, perf_ver);
  switch (perf_ver) {
  case 0:
    /* ERROR("perf monitoring capability is not supported\n"); */
    break;
  case 1:
    /* nr_ctrs = (buf[0] >> 8) & 0xff; */
    /* The bit width of an IA32_PMCx MSR is reported using the
       CPUID.0AH:EAX[23:16]. */
    /* nr_fixed_ctrs = 0; */
    break;
  case 2:
    /* nr_ctrs = (buf[0] >> 8) & 0xff */

    /* Version 2 adds IA32_PERF_GLOBAL_CTRL, IA32_PERF_GLOBAL_STATUS,
       IA32_PERF_GLOBAL_CTRL. */

    /* Bits 0 through 4 of CPUID.0AH.EDX indicates the number
       of fixed-function performance counters available per core.
       It also says that there are 3. */

    /* nr_fixed_ctrs = 3 */

    /* Bits 5 through 12 of CPUID.0AH.EDX indicates the bit-width of
       fixed-function performance counters. Bits beyond the width of
       the fixed-function counter are reserved and must be written as
       zeros. */
    break;
  case 3:
    /* Close enough. */
    rc = 1;
    break;
  default:
    ERROR("unknown perf monitoring version %d\n", perf_ver);
    break;
  }

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

static int begin_pmc_cpu(char *cpu, uint64_t event[4])
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t global_ctr_ctrl, global_ovf_ctrl, fixed_ctr_ctrl;


  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  /* Disable counters globally. */
  global_ctr_ctrl = 0;
  if (pwrite(mds_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0) {
    ERROR("cannot disable performance counters: %m\n");
    goto out;
  }

  int i;
  for (i = 0; i < 4; i++) {
    TRACE("MSR %08X, event %016llX\n", IA32_PERFEVTSEL0 + i, (unsigned long long) event[i]);

    if (pwrite(msr_fd, &event[i], sizeof(event[i]), IA32_PERFEVTSEL0 + i) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) event[i],
            (unsigned) IA32_PERFEVTSEL0 + i,
            msr_path);
      goto out;
    }
  }
  rc = 0;

  /* Enable fixed counters.  Three 4 bit blocks, enable OS, User, Any thread. */
  uint64_t fixed_ctr_ctrl = 0x777;
  if (pwrite(mds_fd, &fixed_ctr_ctrl, sizeof(fixed_ctr_ctrl), IA32_FIXED_CTR_CTRL) < 0)
    ERROR("cannot enable fixed counters: %m\n");

  /* Enable counters globally, 4 PMC and 3 fixed. */
  uint64_t global_ctr_ctrl = 0xF | (0x7ULL << 32);
  if (pwrite(mds_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0)
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

// #define DRAMaccesses   PERF_EVENT(0xE0, 0x07) /* DCT0 only */
// #define HTlink0Use     PERF_EVENT(0xF6, 0x37) /* Counts all except NOPs */
// #define HTlink1Use     PERF_EVENT(0xF7, 0x37) /* Counts all except NOPs */
// #define HTlink2Use     PERF_EVENT(0xF8, 0x37) /* Counts all except NOPs */
// #define UserCycles    (PERF_EVENT(0x76, 0x00) & ~(1UL << 17))
// #define DCacheSysFills PERF_EVENT(0x42, 0x01) /* Counts DCache fills from beyond the L2 cache. */
// #define SSEFLOPS       PERF_EVENT(0x03, 0x7F) /* Counts single & double, add, multiply, divide & sqrt FLOPs. */

static int begin_pmc(struct stats_type *type)
{
#define X(cpu, e0, e1, e2, e3) \
  do { \
    if (cpu_is_nehalem(cpu)) \
      begin_pmc_cpu(cpu, (uint64_t []) { e0, e1, e2, e3 }); \
  } while (0)

//   X("0", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("1", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("2", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("3", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("4", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("5", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("6", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("7", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("8", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("9", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("10", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("11", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("12", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("13", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("14", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
//   X("15", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
#undef X

  return 0;
}

static void collect_pmc_cpu(struct stats_type *type, char *cpu)
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

static void collect_pmc(struct stats_type *type)
{
  const char *path = "/dev/cpu";
  DIR *dir = NULL;

  dir = opendir(path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (!isdigit(ent->d_name[0]))
      continue;
    if (!cpu_is_nehalem(ent->d_name))
      continue;
    collect_pmc_cpu(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type STATS_TYPE_INTEL_PMC3 = {
  .st_name = "intel_pmc3",
  .st_collect = &collect_pmc,
#define X(k,r...) #k
  .st_schema = (char *[]) { KEYS, NULL, },
#undef X
};
