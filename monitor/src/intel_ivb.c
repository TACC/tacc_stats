/*! 
 \file intel_ivb.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Ivy Bridge Processors


  \par Details such as Tables and Figures can be found in:
  "Intel® 64 and IA-32 Architectures Software Developer’s Manual
  Volume 3B: System Programming Guide, Part 2" 
  Order Number: 253669-047US June 2013 \n

  \note
  Ivy Bridge microarchitectures have signatures 06_3e. 
  Non-architectural events are listed in Table 19-7, 19-8, and 19-9.  
  Table 19-8 is 06_2a specific, Table 19-9 is 06_2d specific.  


  \par Location of cpu info and monitoring register files:

  ex) Display cpuid and msr file for cpu 0:

      $ ls -l /dev/cpu/0
      total 0
      crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
      crw-------  1 root root 202, 0 Oct 28 18:47 msr


  \par MSR address layout of registers:

  There are 16 logical processors on Stampede with Hyperthreading disabled.
  There are 8 configurable and 3 fixed counter registers per processor.

  IA32_PMCx (CTRx) MSRs start at address 0C1H and occupy a contiguous block of MSR
  address space; the number of MSRs per logical processor is reported using
  CPUID.0AH:EAX[15:8].  

  IA32_PERFEVTSELx (CTLx) MSRs start at address 186H and occupy a contiguous block
  of MSR address space. Each performance event select register is paired with a
  corresponding performance counter in the 0C1H address block.
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
#include "cpuid.h"
#include "intel_pmc3.h"

/*! \name Events 

  Non-architectural events are listed in Table 19-7, 19-8, and 19-9. 
  Table 19-8 is 06_2a specific, Table 19-9 is 06_2d specific.

  @{
*/
#define DTLB_LOAD_MISSES_WALK_CYCLES   PERF_EVENT(0x08, 0x04)
#define FP_COMP_OPS_EXE_SSE_FP_PACKED  PERF_EVENT(0x10, 0x10)
#define FP_COMP_OPS_EXE_SSE_FP_SCALAR  PERF_EVENT(0x10, 0x80)
#define SSE_DOUBLE_SCALAR_PACKED       PERF_EVENT(0x10, 0x90)
#define SIMD_FP_256_PACKED_DOUBLE      PERF_EVENT(0x11, 0x02)
#define L1D_REPLACEMENT                PERF_EVENT(0x51, 0x01) 
#define RESOURCE_STALLS_ANY            PERF_EVENT(0xA2, 0x01) 
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0xD0, 0x81) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_L1_HIT   PERF_EVENT(0xD1, 0x01) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_L2_HIT   PERF_EVENT(0xD1, 0x02) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_LLC_HIT  PERF_EVENT(0xD1, 0x04) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_LLC_MISS PERF_EVENT(0xD1, 0x20) // CTR0-3 Only
#define MEM_LOAD_UOPS_RETIRED_HIT_LFB  PERF_EVENT(0xD1, 0x40) // CTR0-3 Only
//@}

//! Configure and start counters
static int intel_ivb_begin(struct stats_type *type)
{
  int n_pmcs = 0;
  int nr = 0;

  uint64_t events[] = {
    MEM_UOPS_RETIRED_ALL_LOADS,
    MEM_LOAD_UOPS_RETIRED_L1_HIT,
    MEM_LOAD_UOPS_RETIRED_L2_HIT,
    MEM_LOAD_UOPS_RETIRED_LLC_HIT,
    L1D_REPLACEMENT,
    FP_COMP_OPS_EXE_SSE_FP_SCALAR,
    FP_COMP_OPS_EXE_SSE_FP_PACKED,
    SIMD_FP_256_PACKED_DOUBLE,
  };

  int i;
  if (signature(IVYBRIDGE, &n_pmcs))
    for (i = 0; i < nr_cpus; i++) {
      char cpu[80];
      snprintf(cpu, sizeof(cpu), "%d", i);
      if (intel_pmc3_begin_cpu(cpu, events, n_pmcs) == 0)
	nr++;
    }

  if (nr == 0) 
    type->st_enabled = 0;
  return nr > 0 ? 0 : -1;
}

static void intel_ivb_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);
    intel_pmc3_collect_cpu(type, cpu);
  }
}

//! Definition of stats entry for this type
struct stats_type intel_ivb_stats_type = {
  .st_name = "intel_ivb",
  .st_begin = &intel_ivb_begin,
  .st_collect = &intel_ivb_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
