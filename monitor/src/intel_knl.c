/*! 
 \file intel_knl.c
 \author Todd Evans 
 \brief Performance Monitoring Counters for Intel Sandy Bridge Processors


  \par Details such as Tables and Figures can be found in:
  "Intel® 64 and IA-32 Architectures Software Developer’s Manual
  Volume 3B: System Programming Guide, Part 2" 
  Order Number: 253669-047US June 2013 \n

  \note
  Sandy Bridge microarchitectures have signatures 06_2a and 06_2d. 
  Stampede is 06_2d.
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
#define MEM_UOPS_RETIRED_ALL_LOADS     PERF_EVENT(0x04, 0x40)
#define MEM_UOPS_RETIRED_L2_HIT_LOADS  PERF_EVENT(0x04, 0x02)
//@}

//! Configure and start counters
static int intel_knl_begin(struct stats_type *type)
{  
  int n_pmcs = 0;
  int nr = 0;

  uint64_t events[] = {
    MEM_UOPS_RETIRED_ALL_LOADS,
    MEM_UOPS_RETIRED_L2_HIT_LOADS,
  };

  int i;
  if (signature(KNL, &n_pmcs))
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

static void intel_knl_collect(struct stats_type *type)
{
  int i;
  for (i = 0; i < nr_cpus; i++) {
    char cpu[80];
    snprintf(cpu, sizeof(cpu), "%d", i);
    intel_pmc3_collect_cpu(type, cpu);
  }
}

//! Definition of stats entry for this type
struct stats_type intel_knl_stats_type = {
  .st_name = "intel_knl",
  .st_begin = &intel_knl_begin,
  .st_collect = &intel_knl_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KNL_KEYS),
#undef X
};
