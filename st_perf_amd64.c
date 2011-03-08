#define _GNU_SOURCE
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

// The performance monitor counters are used by software to count
// specific events that occur in the processor.  [The Performance
// Event Select Register (PERF_CTL[3:0])] MSRC001_00[03:00] and [The
// Performance Event Counter Registers (PERF_CTR[3:0])]
// MSRC001_00[07:04] specify the events to be monitored and how they
// are monitored.  All of the events are specified in section 3.14
// [Performance Counter Events].

#define MSR_PERF_CTL0 0xC0010000
#define MSR_PERF_CTL1 0xC0010001
#define MSR_PERF_CTL2 0xC0010002
#define MSR_PERF_CTL3 0xC0010003

#define MSR_PERF_CTR0 0xC0010004
#define MSR_PERF_CTR1 0xC0010005
#define MSR_PERF_CTR2 0xC0010006
#define MSR_PERF_CTR3 0xC0010007

#define PERF_KEYS \
  X(PERF_CTL0), \
  X(PERF_CTL1), \
  X(PERF_CTL2), \
  X(PERF_CTL3), \
  X(PERF_CTR0), \
  X(PERF_CTR1), \
  X(PERF_CTR2), \
  X(PERF_CTR3)

static int cpu_is_family_10h(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[8];
  int rc = 0;

  /* Open /dev/cpuid/CPU/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

  /* Do cpuid 0, 1 to get cpu vendor, family.  */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }

  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  TRACE("cpu %s, vendor `%.12s'\n", cpu, (char*) buf + 4);

  if (strncmp((char*) buf + 4, "AuthenticAMD", 12) != 0)
    goto out;

  unsigned family, base_family, ext_family, model, base_model, ext_model, stepping;

  base_family = (buf[4] >> 8) & 0xF;
  ext_family = (buf[4] >> 20) & 0xFF;
  if (base_family < 0xF)
    family = base_family;
  else
    family = base_family + ext_family;

  base_model = (buf[4] >> 4) & 0xF;
  ext_model = (buf[4] >> 16) & 0xF;
  model = base_model | (ext_model << 4);

  stepping = buf[4] & 0xF;

  TRACE("cpuid 1: eax %X, family %X, model %X, stepping %X\n",
        buf[4], family, model, stepping);

  if (family == 0x10)
    rc = 1;

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

static int begin_perf_cpu(char *cpu, uint64_t event[4])
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;

  if (!cpu_is_family_10h(cpu))
    goto out;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  int i;
  for (i = 0; i < 4; i++) {
    TRACE("MSR %08X, event %016llX\n", MSR_PERF_CTL0 + i, (unsigned long long) event[i]);

    if (pwrite(msr_fd, &event[i], sizeof(event[i]), MSR_PERF_CTL0 + i) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) event[i],
            (unsigned) MSR_PERF_CTL0 + i,
            msr_path);
      goto out;
    }
  }
  rc = 0;

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

#define PERF_EVENT(event_select, unit_mask) \
  ( (event_select & 0xFF) \
  | (unit_mask << 8) \
  | (1UL << 16) /* Count in user mode (CPL == 0). */ \
  | (1UL << 17) /* Count in OS mode (CPL > 0). */ \
  | (1UL << 22) /* Enable. */ \
  | ((event_select & 0xF00) << 24) \
  )

#define DRAMaccesses   PERF_EVENT(0xE0, 0x07) /* DCT0 only */
#define HTlink0Use     PERF_EVENT(0xF6, 0x37) /* Counts all except NOPs */
#define HTlink1Use     PERF_EVENT(0xF7, 0x37) /* Counts all except NOPs */
#define HTlink2Use     PERF_EVENT(0xF8, 0x37) /* Counts all except NOPs */
#define UserCycles    (PERF_EVENT(0x76, 0x00) & ~(1UL << 17))
#define DCacheSysFills PERF_EVENT(0x42, 0x01) /* Counts DCache fills from beyond the L2 cache. */
#define SSEFLOPS       PERF_EVENT(0x03, 0x7F) /* Counts single & double, add, multiply, divide & sqrt FLOPs. */

static int begin_perf(struct stats_type *type)
{
#define X(cpu, e0, e1, e2, e3) \
  begin_perf_cpu(cpu, (uint64_t []) { e0, e1, e2, e3 });

  X("0", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
  X("1", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("2", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("3", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("4", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
  X("5", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("6", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("7", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("8", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
  X("9", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("10", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("11", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("12", DRAMaccesses, UserCycles, DCacheSysFills, SSEFLOPS);
  X("13", HTlink0Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("14", HTlink1Use, UserCycles, DCacheSysFills, SSEFLOPS);
  X("15", HTlink2Use, UserCycles, DCacheSysFills, SSEFLOPS);
#undef X

  return 0;
}

static void collect_perf_cpu(struct stats_type *type, char *cpu)
{
  char msr_path[80];
  int msr_fd = -1;
  struct stats *stats = NULL;

  if (!cpu_is_family_10h(cpu))
    goto out;

  stats = get_current_stats(type, cpu);
  if (stats == NULL)
    goto out;

  /* Read MSRs. */
  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

#define X(K) \
  ({ \
    uint64_t val = 0; \
    if (pread(msr_fd, &val, sizeof(val), MSR_##K) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #K, MSR_##K, msr_path); \
    else \
      stats_set(stats, #K, val); \
  })
  PERF_KEYS;
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
    collect_perf_cpu(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_PERF_AMD64_TYPE = {
  .st_name = "perf_amd64",
  .st_begin = &begin_perf,
  .st_collect = &collect_perf,
#define X(K) #K
  .st_schema = (char *[]) { PERF_KEYS, NULL, },
#undef X
};
