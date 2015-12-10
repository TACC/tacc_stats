/*! 
 \file intel_rapl.c
 \author Todd Evans 
 \brief RAPL Counters for Intel Processors
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
#include <math.h>
#include "stats.h"
#include "trace.h"
#include "cpuid.h"

#define MSR_RAPL_POWER_UNIT        0x606

/*
 * Platform specific RAPL Domains.
 * Note that PP1 RAPL Domain is supported on 062A only
 * And DRAM RAPL Domain is supported on 062D only
 */
/* Package RAPL Domain */
#define MSR_PKG_ENERGY_STATUS      0x611
#define MSR_PKG_POWER_INFO         0x614

/* PP0 RAPL Domain */
#define MSR_PP0_ENERGY_STATUS      0x639

/* PP1 RAPL Domain, may reflect to uncore devices */
#define MSR_PP1_ENERGY_STATUS      0x641

/* DRAM RAPL Domain */
#define MSR_DRAM_ENERGY_STATUS     0x619
#define MSR_DRAM_POWER_INFO        0x61C

/* RAPL UNIT BITMASK */
#define POWER_UNIT_OFFSET          0
#define POWER_UNIT_MASK            0x0F

#define ENERGY_UNIT_OFFSET         0x08
#define ENERGY_UNIT_MASK           0x1F00

#define TIME_UNIT_OFFSET           0x10
#define TIME_UNIT_MASK             0xF000

#define KEYS						\
  X(MSR_PKG_ENERGY_STATUS, "E,W=32,U=mJ", ""),		\
    X(MSR_PP0_ENERGY_STATUS, "E,W=32,U=mJ", ""),		\
    X(MSR_DRAM_ENERGY_STATUS, "E,W=32,U=mJ", "")

static int intel_rapl_begin(struct stats_type *type)
{
  int cpu = 0;
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = -1;

  char vendor[12];
  /* Open /dev/cpuid/CPU/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%d/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

  /* Do cpuid 0 to get cpu vendor. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }
  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  snprintf(vendor, sizeof(vendor) + 1, (char*) buf + 4);
  TRACE("cpu %s, vendor `%.12s'\n", cpu, vendor);
  if (strncmp(vendor, "GenuineIntel", 12) != 0)
    type->st_enabled = 0;  
  rc = 0;
  
 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);
  return rc;
}

static void intel_rapl_collect_socket(struct stats_type *type, char *cpu, int pkg_id)
{
  struct stats *stats = NULL;
  char msr_path[80];
  int msr_fd = -1;
  uint64_t unit_fact;
  double conv;
  char pkg[80];
  
  snprintf(pkg, sizeof(pkg), "%d", pkg_id);

  TRACE("cpu %s pkg %s\n", cpu, pkg);

  stats = get_current_stats(type, pkg);
  if (stats == NULL)
    goto out;

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  if (pread(msr_fd, &unit_fact, sizeof(unit_fact), MSR_RAPL_POWER_UNIT) < 0) {	
    ERROR("cannot read RAPL unit factor: %m\n");
    goto out;
  }      
  
  TRACE("Power unit %lld Energy Unit %lld\n", unit_fact & 0xf, (unit_fact >> 8) & 0x1f);
  conv = 1000*pow(0.5,(double)((unit_fact >> 8) & 0x1f));

#define X(k,r...) \
  ({ \
    uint64_t val = 0; \
    if (pread(msr_fd, &val, sizeof(val), k) < 0) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, k, msr_path); \
    else \
      stats_set(stats, #k, val*conv); \
  })
  KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

//! Collect values of counters
static void intel_rapl_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    int pkg_id = -1;
    int core_id = -1;
    int smt_id = -1;
    int nr_cores = 0;
    snprintf(cpu, sizeof(cpu), "%d", i);
    topology(cpu, &pkg_id, &core_id, &smt_id, &nr_cores);
  
    if (core_id == 0 && smt_id == 0)
      intel_rapl_collect_socket(type, cpu, pkg_id);
  }
}

//! Definition of stats entry for this type
struct stats_type intel_rapl_stats_type = {
  .st_name = "intel_rapl",
  .st_begin = &intel_rapl_begin,
  .st_collect = &intel_rapl_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
