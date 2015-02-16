/*! 
 \file intel_phi.c
 \author Todd Evans 
*/

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


#define MSR_PERF_GLOBAL_CTRL 0x2F // Bits 0,1 enable PMC 0,1

#define MSR_PERF_GLOBAL_STATUS   0x2D //!< Ignore   
#define MSR_PERF_GLOBAL_OVF_CTRL 0x2E //!< Ignore

#define MSR_CTL0 0x28
#define MSR_CTL1 0x29

#define MSR_CTR0 0x20
#define MSR_CTR1 0x21


#define KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTR0, "E,W=40", ""), \
    X(CTR1, "E,W=40", "")

#define PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (1ULL << 16) \
  | (1ULL << 17) \
  | (1ULL << 21) \
  | (1ULL << 22) \
  )

#define VPU_ELEMENTS_ACTIVE       PERF_EVENT(0x20, 0x18)
#define VPU_INSTRUCTIONS_EXECUTED PERF_EVENT(0x20, 0x16)

//! Configure and start counters for a cpu
static int intel_phi_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
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
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), MSR_PERF_GLOBAL_CTRL) < 0) {
    ERROR("cannot disable performance counters: %m\n");
    goto out;
  }

  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", MSR_CTL0 + i, (unsigned long long) events[i]);
    if (pwrite(msr_fd, &events[i], sizeof(events[i]), MSR_CTL0 + i) < 0) {
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
    if (pwrite(msr_fd, &zero, sizeof(zero), MSR_CTR0 + i) < 0) {
      ERROR("cannot reset counter %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) zero,
            (unsigned) MSR_CTR0 + i,
            msr_path);
      goto out;
    }
  }
  
  rc = 0;

  /* Enable counters globally, 2 PMC. */
  global_ctr_ctrl = 0x3
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), MSR_PERF_GLOBAL_CTRL) < 0)
    ERROR("cannot enable performance counters: %m\n");

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

//! Configure and start counters
static int intel_phi_begin(struct stats_type *type)
{
  int nr = 0;

  uint64_t events[] = {
    VPU_ELEMENTS_ACTIVE,
    VPU_INSTRUCTIONS_EXECUTED,
  };

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_sandybridge(cpu))
      if (intel_phi_begin_cpu(cpu, events, 2) == 0)
	nr++;
  }

  return nr > 0 ? 0 : -1;
}

//! Collect values in counters for cpu
static void intel_phi_collect_cpu(struct stats_type *type, char *cpu)
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
    if (pread(msr_fd, &val, sizeof(val), MSR_##k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, MSR_##k, msr_path); \
    else \
      stats_set(stats, #k, val); \
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

//! Collect values in counters
static void intel_phi_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);

    if (cpu_is_sandybridge(cpu))
      intel_phi_collect_cpu(type, cpu);
  }
}

//! Definition of stats entry for this type
struct stats_type intel_phi_stats_type = {
  .st_name = "intel_phi",
  .st_begin = &intel_phi_begin,
  .st_collect = &intel_phi_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
