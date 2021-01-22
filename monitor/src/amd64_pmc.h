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


#define MSR_PERF_CTL0 0xC0010200
#define MSR_PERF_CTL1 0xC0010202
#define MSR_PERF_CTL2 0xC0010204
#define MSR_PERF_CTL3 0xC0010206
#define MSR_PERF_CTL4 0xC0010208
#define MSR_PERF_CTL5 0xC001020A
#define MSR_PERF_CTR0 0xC0010201
#define MSR_PERF_CTR1 0xC0010203
#define MSR_PERF_CTR2 0xC0010205
#define MSR_PERF_CTR3 0xC0010207
#define MSR_PERF_CTR4 0xC0010209
#define MSR_PERF_CTR5 0xC001020B

#define KEYS \
  X(CTL0, "C", ""), \
  X(CTL1, "C", ""), \
  X(CTL2, "C", ""), \
  X(CTL3, "C", ""), \
  X(CTL4, "C", ""), \
  X(CTL5, "C", ""), \
  X(CTR0, "E,W=48", ""), \
  X(CTR1, "E,W=48", ""), \
  X(CTR2, "E,W=48", ""), \
  X(CTR3, "E,W=48", ""), \
  X(CTR4, "E,W=48", ""), \
  X(CTR5, "E,W=48", "")

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


/*
// The performance monitor counters are used by software to count
// specific events that occur in the processor.  [The Performance
// Event Select Register (PERF_CTL[3:0])] MSRC001_00[03:00] and [The
// Performance Event Counter Registers (PERF_CTR[3:0])]
// MSRC001_00[07:04] specify the events to be monitored and how they
// are monitored.  All of the events are specified in section 3.14
// [Performance Counter Events].
//
// In 17H these CTR/CTLs are valid but legacy and just pointers
// to the real registers, however, 17H has an additional 2 
// counters. This is left here in case 10H needs to be supported 
// again (need 10H sig)

#define LEGACY_MSR_PERF_CTL0 0xC0010000
#define LEGACY_MSR_PERF_CTL1 0xC0010001
#define LEGACY_MSR_PERF_CTL2 0xC0010002
#define LEGACY_MSR_PERF_CTL3 0xC0010003
#define LEGACY_MSR_PERF_CTR0 0xC0010004
#define LEGACY_MSR_PERF_CTR1 0xC0010005
#define LEGACY_MSR_PERF_CTR2 0xC0010006
#define LEGACY_MSR_PERF_CTR3 0xC0010007
*/

