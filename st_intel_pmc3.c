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

/* B.4.1 Additional MSRs In the Intel Xeon Processors 5500 and 3400
   Series.  These also apply to Core i7 and i5 processor family CPUID
   signature of 06_1AH, 06_1EH and 06_1FH. */

#define MSR_UNCORE_PERF_GLOBAL_CTRL     0x391
#define MSR_UNCORE_PERF_GLOBAL_STATUS   0x392
#define MSR_UNCORE_PERF_GLOBAL_OVF_CTRL 0x393
#define MSR_UNCORE_FIXED_CTR0           0x394 /* Uncore clock. */
#define MSR_UNCORE_FIXED_CTR_CTRL       0x395
#define MSR_UNCORE_ADDR_OPCODE_MATCH    0x396

#define MSR_UNCORE_PMC0 0x3B0 /* CHECKME */
#define MSR_UNCORE_PMC1 0x3B1
#define MSR_UNCORE_PMC2 0x3B2
#define MSR_UNCORE_PMC3 0x3B3
#define MSR_UNCORE_PMC4 0x3B4
#define MSR_UNCORE_PMC5 0x3B5
#define MSR_UNCORE_PMC6 0x3B6
#define MSR_UNCORE_PMC7 0x3B7

#define MSR_UNCORE_PERFEVTSEL0 0x3C0 /* CHECKME */
#define MSR_UNCORE_PERFEVTSEL1 0x3C1
#define MSR_UNCORE_PERFEVTSEL2 0x3C2
#define MSR_UNCORE_PERFEVTSEL3 0x3C3
#define MSR_UNCORE_PERFEVTSEL4 0x3C4
#define MSR_UNCORE_PERFEVTSEL5 0x3C5
#define MSR_UNCORE_PERFEVTSEL6 0x3C6
#define MSR_UNCORE_PERFEVTSEL7 0x3C7

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

static void collect_perf_cpu(struct stats_type *type, char *cpu)
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

static void collect_perf(struct stats_type *type)
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
    collect_perf_cpu(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_PERF_NEHALEM_TYPE = {
  .st_name = "perf_nehalem",
  .st_collect = &collect_perf,
#define X(k,r...) #k
  .st_schema = (char *[]) { KEYS, NULL, },
#undef X
};
