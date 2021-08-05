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

// RAPL Core::X86::Msr::RAPL_PWR_UNIT
#define MSR_RAPL_PWR_UNIT    0xC0010299
#define MSR_CORE_ENERGY_STAT 0xC001029A
#define MSR_PKG_ENERGY_STAT  0xC001029B


#define KEYS\
    X(MSR_CORE_ENERGY_STAT, "E,W=32,U=mJ", ""),	\
    X(MSR_PKG_ENERGY_STAT, "E,W=32,U=mJ", "")

static double conv;

static int amd64_rapl_begin_cpu(char *cpu)
{
  int rc = -1;
  char msr_path[80];
  int msr_fd = -1;
  
  // 17H and 19H have RAPL Counters (Core and Pkg) we can access.
  switch(processor) {
  case AMD_17H:
    break;
  case AMD_19H:
    break;
  default:
    TRACE("Processor model/family %d not supported by AMD RAPL\n", processor);
    goto out;
  }

  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDWR);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }
    
  rc = 0;
  
 out:
  if (msr_fd >= 0)
    close(msr_fd);
  
  return rc;
}

static void amd64_rapl_collect_cpu(struct stats_type *type, char *cpu, char *socket, int core)
{
  char msr_path[80];
  int msr_fd = -1;
  struct stats *stats = NULL;

  
  stats = get_current_stats(type, socket);
  if (stats == NULL)
    goto out;

  /* Read MSRs. */
  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  {  
    uint64_t val = 0;						    
    if (pread(msr_fd, &val, sizeof(val), MSR_RAPL_PWR_UNIT) < 0) {
      TRACE("cannot read `RAPL' unit factor (%08X) through `%s': %m\n", MSR_RAPL_PWR_UNIT, msr_path);
      goto out;
    }
    
    TRACE("Power unit %lld Energy Unit %lld\n", val & 0xf, (val >> 8) & 0x1f);  
    conv = 1000*pow(0.5,(double)((val >> 8) & 0x1f)); // milli-Joules
  }

#define X(k,r...)							\
  ({									\
    uint64_t val = 0;							\
    if (pread(msr_fd, &val, sizeof(val), k) < 0)			\
      TRACE("cannot read `%s' (%08X) through `%s': %m\n", #k, k, msr_path); \
    else								\
      stats_inc(stats, #k, val*conv);					\
  })
  X(MSR_CORE_ENERGY_STAT, "E,W=32,U=mJ", "");
#undef X
  
  if (core == 0) {
#define X(k,r...)							\
    ({									\
      uint64_t val = 0;							\
      if (pread(msr_fd, &val, sizeof(val), k) < 0)			\
	TRACE("cannot read `%s' (%08X) through `%s': %m\n", #k, k, msr_path); \
      else								\
	stats_inc(stats, #k, val*conv);					\
    })
    X(MSR_PKG_ENERGY_STAT, "E,W=32,U=mJ", "");
#undef X
  }
  

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}

static void amd64_rapl_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);
    int pkg, core, smt, nr_core;

    if (topology(cpu, &pkg, &core, &smt, &nr_core) && (smt == 0)) {
      char pkg_str[80];
      snprintf(pkg_str, sizeof(pkg_str), "%d", pkg);
      amd64_rapl_collect_cpu(type, cpu, pkg_str, core);
    }
  }
}

static int amd64_rapl_begin(struct stats_type *type)
{
  int nr = 0;

  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);
    int pkg, core, smt, nr_core;
    
    if (topology(cpu, &pkg, &core, &smt, &nr_core) && (core == 0) && (smt == 0))
      if (amd64_rapl_begin_cpu(cpu) == 0)
	nr++;
  }
  
  if (nr == 0)
    type->st_enabled = 0;
  return nr > 0 ? 0 : -1;
}

struct stats_type amd64_rapl_stats_type = {
  .st_name = "amd64_rapl",
  .st_begin = &amd64_rapl_begin,
  .st_collect = &amd64_rapl_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
