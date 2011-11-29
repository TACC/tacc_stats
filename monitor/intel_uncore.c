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

/* B.4.1 Additional MSRs In the Intel Xeon Processors 5500 and 3400
   Series.  These also apply to Core i7 and i5 processor family CPUID
   signature of 06_1AH, 06_1EH and 06_1FH. */

#define MSR_UNCORE_PERF_GLOBAL_CTRL     0x391
#define MSR_UNCORE_PERF_GLOBAL_STATUS   0x392 /* Overflow bits for PC{0..7}, FC0, PMI, CHG. */
#define MSR_UNCORE_PERF_GLOBAL_OVF_CTRL 0x393 /* Write to clear status bits. */
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
  X(FIXED_CTR0, "E,W=48", "uncore clock"), \
  X(FIXED_CTR_CTRL, "C", ""), \
  X(ADDR_OPCODE_MATCH, "C", ""), \
  X(PMC0, "E,W=48", ""), \
  X(PMC1, "E,W=48", ""), \
  X(PMC2, "E,W=48", ""), \
  X(PMC3, "E,W=48", ""), \
  X(PMC4, "E,W=48", ""), \
  X(PMC5, "E,W=48", ""), \
  X(PMC6, "E,W=48", ""), \
  X(PMC7, "E,W=48", ""), \
  X(PERFEVTSEL0, "C", ""), \
  X(PERFEVTSEL1, "C", ""), \
  X(PERFEVTSEL2, "C", ""), \
  X(PERFEVTSEL3, "C", ""), \
  X(PERFEVTSEL4, "C", ""), \
  X(PERFEVTSEL5, "C", ""), \
  X(PERFEVTSEL6, "C", ""), \
  X(PERFEVTSEL7, "C", "")

/* Volume 3B: Non-architectural Performance monitoring events of the
   uncore sub-system for Processors with CPUID signature of
   DisplayFamily_DisplayModel 06_25H, 06_2CH, and 06_1FH support
   performance events listed in Table A-7. */

#define CPU_IS_WESTMERE(family, model) \
  ((family) == 6 && (((model) == 0x25) || ((model) == 0x2c) || ((model) == 0x1f)))

#define UNC_EVENT(sel, mask) ((sel) | ((mask) << 8) | (1 << 22))

#define UNC_L3_HITS_READ UNC_EVENT(0x08, 0x01)
  /* Number of code read, data read and RFO requests that hit in the L3. */
#define UNC_L3_HITS_WRITE UNC_EVENT(0x08, 0x02)
  /* Number of writeback requests that hit in the L3. Writebacks from
     the cores will always result in L3 hits due to the inclusive
     property of the L3. */
#define UNC_L3_HITS_PROBE UNC_EVENT(0x08, 0x04)
  /* Number of snoops from IOH or remote sockets that hit in the L3. */
#define UNC_L3_MISS_READ UNC_EVENT(0x09, 0x01)
  /* Number of code read, data read and RFO requests that miss the L3. */
#define UNC_L3_MISS_WRITE UNC_EVENT(0x09, 0x02)
  /* Number of writeback requests that miss the L3. Should always be
     zero as writebacks from the cores will always result in L3 hits
     due to the inclusive property of the L3. */
#define UNC_L3_MISS_PROBE UNC_EVENT(0x09, 0x04)
  /* Number of snoops from IOH or remote sockets that miss the L3. */
#define UNC_L3_LINES_IN_ANY UNC_EVENT(0x0a, 0x0f)
  /* Counts the number of L3 lines allocated in any state. */
#define UNC_L3_LINES_OUT_ANY UNC_EVENT(0x0b, 0x1f)
  /* Counts the number of L3 lines victimized in any state. */

static int cpu_is_westmere(char *cpu)
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

  if (pread(cpuid_fd, buf, sizeof(buf), 0x01) < 0) {
    ERROR("cannot read `%s': %m\n", cpuid_path);
    goto out;
  }

  TRACE("cpu %s, cpuid.1 buf %08x %08x %08x %08x\n", cpu, buf[0], buf[1], buf[2], buf[3]);

  unsigned int stepping = buf[0] & 0xf;
  unsigned int model = ((buf[0] & 0xf0) >> 4) | ((buf[0] & 0xf0000) >> 12);
  unsigned int family = (buf[0] & 0xf00) >> 8;

  rc = CPU_IS_WESTMERE(family, model); 

  TRACE("cpu %s, family %x, model %x, stepping %x, rc %d\n", cpu, family, model, stepping, rc);

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

static int intel_uncore_begin_cpu(struct stats_type *type, const char *cpu)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t global_ctr_ctrl, fixed_ctr_ctrl;

  uint64_t events[] = {
    UNC_L3_HITS_READ,
    UNC_L3_HITS_WRITE,
    UNC_L3_HITS_PROBE,
    UNC_L3_MISS_READ,
    UNC_L3_MISS_WRITE,
    UNC_L3_MISS_PROBE,
    UNC_L3_LINES_IN_ANY,
    UNC_L3_LINES_OUT_ANY,
  };
  size_t i, nr_events = sizeof(events) / sizeof(events[0]);

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  /* Disable counters globally. */
  global_ctr_ctrl = 0;
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), MSR_UNCORE_PERF_GLOBAL_CTRL) < 0) {
    ERROR("cannot disable performance counters: %m\n");
    goto out;
  }

  for (i = 0; i < nr_events; i++) {
    unsigned msr = MSR_UNCORE_PERFEVTSEL0 + i;
    TRACE("MSR %08X, event %016llX\n", msr, (unsigned long long) events[i]);

    if (pwrite(msr_fd, &events[i], sizeof(events[i]), msr) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) events[i], msr, msr_path);
      goto out;
    }
  }
  rc = 0;

  fixed_ctr_ctrl = 1;  /* EN_FC0, no PMI on overflow. */
  if (pwrite(msr_fd, &fixed_ctr_ctrl, sizeof(fixed_ctr_ctrl), MSR_UNCORE_FIXED_CTR_CTRL) < 0)
    ERROR("cannot enable uncore fixed counter: %m\n");

  global_ctr_ctrl = 0xff | (1ull << 32); /* EN_PC{0..7} and EN_FC0 */
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), MSR_UNCORE_PERF_GLOBAL_CTRL) < 0)
    ERROR("cannot enable uncore performance counters: %m\n");

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

static int intel_uncore_begin(struct stats_type *type)
{
  int i, nr = 0;
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
    if (!cpu_is_westmere(cpu))
      continue;

    if (intel_uncore_begin_cpu(type, cpu) == 0)
      nr++;
  }

  return nr > 0 ? 0 : -1;
}

static void intel_uncore_collect_cpu(struct stats_type *type, char *cpu)
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

static void intel_uncore_collect(struct stats_type *type)
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

    /* Only collect uncore counters on core 0 of a socket. */
    snprintf(core_id_path, sizeof(core_id_path), "/sys/devices/system/cpu/cpu%d/topology/core_id", i);
    if (pscanf(core_id_path, "%d", &core_id) != 1) {
      ERROR("cannot read core id file `%s': %m\n", core_id_path); /* errno */
      continue;
    }

    if (core_id != 0)
      continue;

    snprintf(cpu, sizeof(cpu), "%d", i);
    if (!cpu_is_westmere(cpu))
      continue;

    intel_uncore_collect_cpu(type, cpu);
  }
}

struct stats_type intel_uncore_stats_type = {
  .st_name = "intel_uncore",
  .st_begin = &intel_uncore_begin,
  .st_collect = &intel_uncore_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
