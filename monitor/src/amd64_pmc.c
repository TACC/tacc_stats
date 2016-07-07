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

#define KEYS \
  X(CTL0, "C", ""), \
  X(CTL1, "C", ""), \
  X(CTL2, "C", ""), \
  X(CTL3, "C", ""), \
  X(CTR0, "E,W=48", ""), \
  X(CTR1, "E,W=48", ""), \
  X(CTR2, "E,W=48", ""), \
  X(CTR3, "E,W=48", "")
/*
static int cpu_is_amd64_10h(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[8];
  int rc = 0;

  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

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
*/
static int amd64_pmc_begin_cpu(char *cpu, uint64_t events[], size_t nr_events)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", MSR_PERF_CTL0 + i, (unsigned long long) events[i]);

    if (pwrite(msr_fd, &events[i], sizeof(events[i]), MSR_PERF_CTL0 + i) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) events[i],
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

/* From the 10h BKDG, p. 403, "The performance counter registers can
   be used to track events in the Northbridge. Northbridge events
   include all memory controller events, crossbar events, and
   HyperTransportTM interface events as documented in 3.14.7, 3.14.8,
   and 3.14.9. Monitoring of Northbridge events should only be
   performed by one core.  If a Northbridge event is selected using
   one of the Performance Event-Select registers in any core of a
   multi-core processor, then a Northbridge performance event cannot
   be selected in the same Performance Event Select register of any
   other core. */

/* Northbridge events. */
#define DRAMaccesses   PERF_EVENT(0xE0, 0x07) /* DCT0 only */
#define HTlink0Use     PERF_EVENT(0xF6, 0x37) /* Counts all except NOPs */
#define HTlink1Use     PERF_EVENT(0xF7, 0x37) /* Counts all except NOPs */
#define HTlink2Use     PERF_EVENT(0xF8, 0x37) /* Counts all except NOPs */
/* Core events. */
#define UserCycles    (PERF_EVENT(0x76, 0x00) & ~(1UL << 17))
#define DCacheSysFills PERF_EVENT(0x42, 0x01) /* Counts DCache fills from beyond the L2 cache. */
#define SSEFLOPS       PERF_EVENT(0x03, 0x7F) /* Counts single & double, add, multiply, divide & sqrt FLOPs. */

static int amd64_pmc_begin(struct stats_type *type)
{
  int n_pmcs = 0;
  int nr = 0;

  uint64_t events[4][4] = {
    { DRAMaccesses, UserCycles,     DCacheSysFills, SSEFLOPS, },
    { UserCycles,   HTlink0Use,     DCacheSysFills, SSEFLOPS, },
    { UserCycles,   DCacheSysFills, HTlink1Use,     SSEFLOPS, },
    { UserCycles,   DCacheSysFills, SSEFLOPS,       HTlink2Use, },
  };

  int i;
  if (signature(AMD_10H, &n_pmcs))
    for (i = 0; i < nr_cpus; i++) {
      char cpu[80];
      snprintf(cpu, sizeof(cpu), "%d", i);
      if (amd64_pmc_begin_cpu(cpu, events[i % 4], n_pmcs) == 0)
        nr++;
    }

  if (nr == 0)
    type->st_enabled = 0;
  return nr > 0 ? 0 : -1;
}

static void amd64_pmc_collect_cpu(struct stats_type *type, char *cpu, int nr_events)
{
  char msr_path[80];
  int msr_fd = -1;
  struct stats *stats = NULL;

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
  int ctr = 0;
#define X(k,r...)							\
  ({									\
    uint64_t val = 0;							\
    if (pread(msr_fd, &val, sizeof(val), MSR_PERF_##k) < 0)		\
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, MSR_PERF_##k, msr_path); \
    else								\
      stats_set(stats, #k, val);					\
    if (++ctr == nr_events)						\
      goto out;								\
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

static void amd64_pmc_collect(struct stats_type *type)
{
  int n_pmcs = 0;
  int i;
  if (signature(AMD_10H, &n_pmcs))
    for (i = 0; i < nr_cpus; i++) {
      char cpu[80];
      snprintf(cpu, sizeof(cpu), "%d", i);
      amd64_pmc_collect_cpu(type, cpu, n_pmcs);
    }
}

struct stats_type amd64_pmc_stats_type = {
  .st_name = "amd64_pmc",
  .st_begin = &amd64_pmc_begin,
  .st_collect = &amd64_pmc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
