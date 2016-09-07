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

/*! 
 \file intel_pmc3.h
 \author Todd Evans 
 \brief Counters for Intel Performance Monitoring Version 3

  \par Location of cpu info and monitoring register files:

  ex) Display cpuid and msr file for cpu 0:

      $ ls -l /dev/cpu/0
      total 0
      crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
      crw-------  1 root root 202, 0 Oct 28 18:47 msr


  \par MSR address layout of registers:

  IA32_PMCx (CTRx) MSRs start at address 0C1H and occupy a contiguous block of MSR
  address space; the number of MSRs per logical processor is reported using
  CPUID.0AH:EAX[15:8].  

  IA32_PERFEVTSELx (CTLx) MSRs start at address 186H and occupy a contiguous block
  of MSR address space. Each performance event select register is paired with a
  corresponding performance counter in the 0C1H address block.
*/

#define IA32_CTR0 0xC1 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_CTR1 0xC2 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_CTR2 0xC3 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_CTR3 0xC4 /* CPUID.0AH: EAX[15:8] > 3 */
#define IA32_CTR4 0xC5 /* CPUID.0AH: EAX[15:8] > 4 */
#define IA32_CTR5 0xC6 /* CPUID.0AH: EAX[15:8] > 5 */
#define IA32_CTR6 0xC7 /* CPUID.0AH: EAX[15:8] > 6 */
#define IA32_CTR7 0xC8 /* CPUID.0AH: EAX[15:8] > 7 */

#define IA32_CTL0 0x186 /* CPUID.0AH: EAX[15:8] > 0 */
#define IA32_CTL1 0x187 /* CPUID.0AH: EAX[15:8] > 1 */
#define IA32_CTL2 0x188 /* CPUID.0AH: EAX[15:8] > 2 */
#define IA32_CTL3 0x189 /* CPUID.0AH: EAX[15:8] > 3 */
#define IA32_CTL4 0x18A /* CPUID.0AH: EAX[15:8] > 4 */
#define IA32_CTL5 0x18B /* CPUID.0AH: EAX[15:8] > 5 */
#define IA32_CTL6 0x18C /* CPUID.0AH: EAX[15:8] > 6 */
#define IA32_CTL7 0x18D /* CPUID.0AH: EAX[15:8] > 7 */

/*! \name Fixed Counter Registers

  These counters always count the same events.
  @{
*/
#define IA32_FIXED_CTR_CTRL 0x38D //!< Fixed Counter Control Register
#define IA32_FIXED_CTR0     0x309 //!< Fixed Counter 0: Instructions Retired
#define IA32_FIXED_CTR1     0x30A //!< Fixed Counter 1: Core Clock Cycles
#define IA32_FIXED_CTR2     0x30B //!< Fixed Counter 2: Reference Clock Cycles
//@}

/*! \name Global Control Registers
  
  Controls for all registers.
  @{
*/
#define IA32_PERF_GLOBAL_STATUS   0x38E //!< indicates overflow 
#define IA32_PERF_GLOBAL_CTRL     0x38F //!< enables all fixed and configurable counters
#define IA32_PERF_GLOBAL_OVF_CTRL 0x390 //!< clears overflow indicators in GLOBAL_STATUS.
//@}

/* Schema Keys 
   All counter registers are 48 bits wide. 
*/

#define KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", ""), \
    X(CTL4, "C", ""), \
    X(CTL5, "C", ""), \
    X(CTL6, "C", ""), \
    X(CTL7, "C", ""), \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", ""), \
    X(CTR4, "E,W=48", ""), \
    X(CTR5, "E,W=48", ""), \
    X(CTR6, "E,W=48", ""), \
    X(CTR7, "E,W=48", ""), \
    X(FIXED_CTR0, "E,W=48", ""), \
    X(FIXED_CTR1, "E,W=48", ""), \
    X(FIXED_CTR2, "E,W=48", "")

#define HT_KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", ""), \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", ""), \
    X(FIXED_CTR0, "E,W=48", ""), \
    X(FIXED_CTR1, "E,W=48", ""), \
    X(FIXED_CTR2, "E,W=48", "")
/* Schema Keys 
   All counter registers are 48 bits wide. 
*/
#define KNL_KEYS		 \
  X(CTL0, "C", ""),		 \
    X(CTL1, "C", ""),		 \
    X(CTR0, "E,W=40", ""),	 \
    X(CTR1, "E,W=40", ""),	 \
    X(FIXED_CTR0, "E,W=40", ""), \
    X(FIXED_CTR1, "E,W=40", ""), \
    X(FIXED_CTR2, "E,W=40", "")



/*! \brief Event select */
// IA32_PERFEVTSELx MSR layout
//   [0, 7] Event Select
//   [8, 15] Unit Mask (UMASK)
//   16 USR
//   17 OS
//   18 E Edge_detect
//   19 PC Pin control
//   20 INT APIC interrupt enable
//   21 ANY Any thread (version 3)
//   22 EN Enable counters
//   23 INV Invert counter mask
//   [24, 31] Counter Mask (CMASK)
//   [32, 63] Reserved
#define PERF_EVENT(event, umask) \
  ( (event)			 \
    | (umask << 8)		 \
    | (1ULL << 16)		 \
    | (1ULL << 17)		 \
    | (1ULL << 21)		 \
    | (1ULL << 22)		 \
    )

//! Generate bitmask of n 1s
#define BIT_MASK(n) (~( ((~0ULL) << ((n)-1)) << 1 ))

//! Configure and start counters for a pmc3 cpu counters
static int intel_pmc3_begin_cpu(char *cpu, uint64_t *events, size_t nr_events)
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
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0) {
    ERROR("cannot disable performance counters: %m\n");
    goto out;
  }

  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("MSR %08X, event %016llX\n", IA32_CTL0 + i, (unsigned long long) events[i]);
    if (pwrite(msr_fd, &events[i], sizeof(events[i]), IA32_CTL0 + i) < 0) {
      ERROR("cannot write event %016llX to MSR %08X through `%s': %m\n",
            (unsigned long long) events[i],
            (unsigned) IA32_CTL0 + i,
            msr_path);
      goto out;
    }
  }
  
  rc = 0;

  /* Enable fixed counters.  Three 4 bit blocks, enable OS, User, Turn off any thread. */
  fixed_ctr_ctrl = 0x333UL;

  if (pwrite(msr_fd, &fixed_ctr_ctrl, sizeof(fixed_ctr_ctrl), IA32_FIXED_CTR_CTRL) < 0)
    ERROR("cannot enable fixed counters: %m\n");

  /* Enable counters globally, nr_events PMC and 3 fixed. */
  global_ctr_ctrl = BIT_MASK(nr_events) | (0x7ULL << 32);
  if (pwrite(msr_fd, &global_ctr_ctrl, sizeof(global_ctr_ctrl), IA32_PERF_GLOBAL_CTRL) < 0)
    ERROR("cannot enable performance counters: %m\n");

 out:
  if (msr_fd >= 0)
    close(msr_fd);

  return rc;
}

//! Collect values in counters for cpu
static void intel_pmc3_collect_cpu(struct stats_type *type, char *cpu)
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

#define X(k,r...)							\
    ({									\
      uint64_t val = 0;							\
      if (pread(msr_fd, &val, sizeof(val), IA32_##k) < 0)		\
	TRACE("cannot read `%s' (%08X) through `%s': %m\n", #k, IA32_##k, msr_path); \
      else								\
	stats_set(stats, #k, val);					\
    })
    KEYS;
#undef X

 out:
  if (msr_fd >= 0)
    close(msr_fd);
}
