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
#include "amd64_pmc.h"

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

static int amd64_pmc_begin(struct stats_type *type)
{
  int n_pmcs = 0;
  int nr = 0;

  // 10H cpus only have 4 counters, 17H has 6.
  uint64_t events[1][6] = { EVENT_MIX_17H };

  // Determine how many different event mixes we have
  int n_event_mix = sizeof(events)/sizeof(events[0]);

  processor_t sig = signature(&n_pmcs);
  int i;
  if (sig == AMD_17H)
    for (i = 0; i < nr_cpus; i++) {
      char cpu[80];
      snprintf(cpu, sizeof(cpu), "%d", i);
      if (amd64_pmc_begin_cpu(cpu, events[i % n_event_mix], n_pmcs) == 0)
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
  if (signature(&n_pmcs) == AMD_17H)
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
