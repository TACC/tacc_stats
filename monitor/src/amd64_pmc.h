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


// From https://developer.amd.com/resources/developer-guides-manuals/
// Open-Source Register Reference for AMD Family 17h Processors
//
// CTLs p. 136 
// MSRC001_020[0...A] [Performance Event Select [5:0]] (Core::X86::Msr::PERF_CTL)
//
// CTRs p. 138
// MSRC001_020[1...B] [Performance Event Counter [5:0]] (Core::X86::Msr::PERF_CTR)

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

// SSE/AVX operations p. 151
// PMCx003 [Retired SSE/AVX Operations] (Core::X86::Pmc::Core::FpRetSseAvxOps)
#define SSEFLOPS_SINGLE       PERF_EVENT(0x03, 0x0F) /* Counts single precision, add, multiply, divide & sqrt FLOPs. */
#define SSEFLOPS_DOUBLE       PERF_EVENT(0x03, 0xF0) /* Counts double precision, add, multiply, divide & sqrt FLOPs. */

// Frequency Counts p. 78
// MSR0000_00E7 [Max Performance Frequency Clock Count] (Core::X86::Msr::MPERF)
// MSR0000_00E8 [Actual Performance Frequency Clock Count] (Core::X86::Msr::APERF)
#define MAX_FREQ            PERF_EVENT(0xE7, 0x00)
#define ACTUAL_FREQ         PERF_EVENT(0xE8, 0x00)

// Pipeline Stalls p. 157
// PMCx087 [Instruction Pipe Stall] (Core::X86::Pmc::Core::IcFetchStall)
#define PIPE_STALLS        PERF_EVENT(0x87, 0x04) 

// DRAM Access p.147
// MSRC001_1036 [IBS Op Data 2] (Core::X86::Msr::IBS_OP_DATA2)
#define DRAM_ACCESS        PERF_EVENT(0x11036, 0x03)

#define EVENT_MIX_17H { SSEFLOPS_SINGLE, SSEFLOPS_DOUBLE, MAX_FREQ, ACTUAL_FREQ, PIPE_STALLS, DRAM_ACCESS }

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



/* LEGACY 10H Counters and Events
 * Left in case 10H needs to be added back


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
//#define DRAMaccesses   PERF_EVENT(0xE0, 0x07) /* DCT0 only */
//#define HTlink0Use     PERF_EVENT(0xF6, 0x37) /* Counts all except NOPs */
//#define HTlink1Use     PERF_EVENT(0xF7, 0x37) /* Counts all except NOPs */
//#define HTlink2Use     PERF_EVENT(0xF8, 0x37) /* Counts all except NOPs */
/* Core events. */
//#define UserCycles    (PERF_EVENT(0x76, 0x00) & ~(1UL << 17))
//#define DCacheSysFills PERF_EVENT(0x42, 0x01) /* Counts DCache fills from beyond the L2 cache. */
//#define SSEFLOPS       PERF_EVENT(0x03, 0x7F) /* Counts single & double, add, multiply, divide & sqrt FLOPs. */


