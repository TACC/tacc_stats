#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <errno.h>
#include <ctype.h>
#include <fcntl.h>
#include "stats.h"
#include "trace.h"
#include "pscanf.h"

/* TODO Implement begin(). */

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

#define KEYS \
  X(PERF_GLOBAL_CTRL, "C", ""), \
  X(PERF_GLOBAL_STATUS, "C", ""), \
  X(PERF_GLOBAL_OVF_CTRL, "C", ""), \
  X(FIXED_CTR0, "E", ""), \
  X(FIXED_CTR_CTRL, "C", ""), \
  X(ADDR_OPCODE_MATCH, "C", ""), \
  X(PMC0, "E", ""), \
  X(PMC1, "E", ""), \
  X(PMC2, "E", ""), \
  X(PMC3, "E", ""), \
  X(PMC4, "E", ""), \
  X(PMC5, "E", ""), \
  X(PMC6, "E", ""), \
  X(PMC7, "E", ""), \
  X(PERFEVTSEL0, "C", ""), \
  X(PERFEVTSEL1, "C", ""), \
  X(PERFEVTSEL2, "C", ""), \
  X(PERFEVTSEL3, "C", ""), \
  X(PERFEVTSEL4, "C", ""), \
  X(PERFEVTSEL5, "C", ""), \
  X(PERFEVTSEL6, "C", ""), \
  X(PERFEVTSEL7, "C", "")

/* XXX Also defined in intel_pmc3. */
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
  default:
    ERROR("unknown perf monitoring version %d\n", perf_ver);
    break;
  case 0:
    break;
  case 1:
    break;
  case 2:
    break;
  case 3:
    /* Close enough. */
    rc = 1;
    break;
  }

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

static void collect_uncore_cpu(struct stats_type *type, char *cpu)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;

  /* FIXME Use cpu's physical package id at device name. */

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
    if (pread(msr_fd, &val, sizeof(val), MSR_UNCORE_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, MSR_UNCORE_##k, msr_path); \
    else \
      stats_set(stats, #k, val); \
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

static void collect_uncore(struct stats_type *type)
{
  // $ cd /sys/devices/system/cpu/cpu0/topology
  // $ for f in *; do echo $f $(cat $f); done
  // core_id 0
  // core_siblings 00000555
  // physical_package_id 1
  // thread_siblings 00000001

  /* It's weird. */
  // $ ./cpu-topology.sh
  // CPU             CORE_ID         CORE_SIBLINGS   PKG_ID          THREAD_SIBLINGS
  // cpu0            0               00000555        1               00000001
  // cpu1            0               00000aaa        0               00000002
  // cpu10           10              00000555        1               00000400
  // cpu11           10              00000aaa        0               00000800
  // cpu2            1               00000555        1               00000004
  // cpu3            1               00000aaa        0               00000008
  // cpu4            2               00000555        1               00000010
  // cpu5            2               00000aaa        0               00000020
  // cpu6            8               00000555        1               00000040
  // cpu7            8               00000aaa        0               00000080
  // cpu8            9               00000555        1               00000100
  // cpu9            9               00000aaa        0               00000200

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    char core_id_path[80];
    int core_id = -1;

    snprintf(cpu, sizeof(cpu), "%d", i);
    if (!cpu_is_nehalem(cpu))
      continue;

    /* Only collect uncore counters on core 0. */

    snprintf(core_id_path, sizeof(core_id_path), "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path); /* errno */
      continue;
    }

    if (core_id != 0)
      continue;

    collect_uncore_cpu(type, cpu);
  }
}

struct stats_type STATS_TYPE_INTEL_UNCORE = {
  .st_name = "intel_uncore",
  .st_collect = &collect_uncore,
#define X(k,o,d,r...) #k "," o
  .st_schema_def = STRJOIN(KEYS),
#undef X
};
