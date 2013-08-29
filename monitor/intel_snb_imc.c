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
#include "pscanf.h"

// Uncore iMC (Memory Controller) events are counted in this file.  The events are accesses in PCI config space.

// Sandy Bridge microarchitectures have signatures 06_2a and 06_2d with non-architectural events
// listed in Table 19-7, 19-8, and 19-9.  19-8 is 06_2a specific, 19-9 is 06_2d specific.  Stampede
// is 06_2d but no 06_2d specific events are used here.

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// $ lspci | grep "Memory Controller Channel"
/*
7f:10.0 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 0 (rev 07)
7f:10.1 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 1 (rev 07)
7f:10.4 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 2 (rev 07)
7f:10.5 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 3 (rev 07)
ff:10.0 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 0 (rev 07)
ff:10.1 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 1 (rev 07)
ff:10.4 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 2 (rev 07)
ff:10.5 System peripheral: Intel Corporation Xeon E5/Core i7 Integrated Memory Controller Channel 0-3 Thermal Control 3 (rev 07)
*/

// Info for this stuff is in: 
//Intel Xeon Processor E5-2600 Product Family Uncore Performance Monitoring Guide
// 4 MCs w/ 4 counters each per socket
// PCI Config Space Dev ID:
// Socket 1: 7f:10.0, 7f:10.1, 7f:10.4, 7f:10.5 
// Socket 0: ff:10.0, 7f:10.1, ff:10.4, ff:10.5 
// Supposedly all registers are 32 bit, but counter
// registers A and B need to be added to get counter value

// Defs in Table 2-59
#define MC_BOX_CTL         0xF4
#define MC_FIXED_CTL       0xF0
#define MC_CTL0           0xD8
#define MC_CTL1           0xDC
#define MC_CTL2           0xE0
#define MC_CTL3           0xE4

#define MC_B_CTR0         0xA0
#define MC_A_CTR0         0xA4
#define MC_B_CTR1         0xA8
#define MC_A_CTR1         0xAC
#define MC_B_CTR2         0xB0
#define MC_A_CTR2         0xB4
#define MC_B_CTR3         0xB8
#define MC_A_CTR3         0xBC
#define MC_B_FIXED_CTR     0xD0
#define MC_A_FIXED_CTR     0xD4

// Width of 44 for C-Boxes
#define CTL_KEYS \
    X(CTL0, "C", ""), \
    X(CTL1, "C", ""), \
    X(CTL2, "C", ""), \
    X(CTL3, "C", "")

#define CTR_KEYS \
    X(CTR0, "E,W=48", ""), \
    X(CTR1, "E,W=48", ""), \
    X(CTR2, "E,W=48", ""), \
    X(CTR3, "E,W=48", ""), \
    X(FIXED_CTR,"E,W=48","")

#define KEYS CTL_KEYS, CTR_KEYS

static void get_cpuid_signature(int cpuid_file, char* signature)
{
  int ebx = 0, ecx = 0, edx = 0, eax = 1;
  __asm__ ("cpuid": "=b" (ebx), "=c" (ecx), "=d" (edx), "=a" (eax):"a" (eax));

  int model = (eax & 0x0FF) >> 4;
  int extended_model = (eax & 0xF0000) >> 12;
  int family_code = (eax & 0xF00) >> 8;
  int extended_family_code = (eax & 0xFF00000) >> 16;

  snprintf(signature,sizeof(signature),"%02x_%x", extended_family_code | family_code, extended_model | model);

}
static int cpu_is_sandybridge(char *cpu)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  uint32_t buf[4];
  int rc = 0;
  char signature[5];

  /* Open /dev/cpuid/cpu/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }
  
  /* Get cpu vendor. */
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }

  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  TRACE("cpu %s, vendor `%.12s'\n", cpu, (char*) buf + 4);

  if (strncmp((char*) buf + 4, "GenuineIntel", 12) != 0)
    goto out; /* CentaurHauls? */

  get_cpuid_signature(cpuid_fd,signature);
  TRACE("cpu%s, CPUID Signature %s\n", cpu, signature);
  if (strncmp(signature, "06_2a", 5) !=0 && strncmp(signature, "06_2d", 5) !=0)
    goto out;

  rc = 1;

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

/* Events in Memory Controller
threshhold        [31:24]
invert threshold  [23]
enable            [22]
edge detect       [18]
umask             [15:8]
event select      [7:0]
*/

/* Defs in Table 2-61 */
#define MBOX_PERF_EVENT(event, umask) \
  ( (event) \
  | (umask << 8) \
  | (0UL << 18) /* Edge Detection. */ \
  | (1UL << 22) /* Enable. */ \
  | (0UL << 23) /* Invert */ \
  | (0x01UL << 24) /* Threshold */ \
  )

/* Definitions in Table 2-14 */
#define CAS_READS           MBOX_PERF_EVENT(0x04, 0x01)
#define CAS_WRITES          MBOX_PERF_EVENT(0x04, 0x0C)
#define ACT_COUNT           MBOX_PERF_EVENT(0x01, 0x00)
#define PRE_COUNT_ALL       MBOX_PERF_EVENT(0x02, 0x03)

static int intel_snb_imc_begin_dev(char *bus_dev, uint32_t *events, size_t nr_events)
{
  int rc = -1;
  char pci_path[80];
  int pci_fd = -1;
  uint32_t ctl;

  snprintf(pci_path, sizeof(pci_path), "/proc/bus/pci/%s", bus_dev);
  pci_fd = open(pci_path, O_RDWR);
  if (pci_fd < 0) {
    ERROR("cannot open `%s': %m\n", pci_path);
    goto out;
  }

  ctl = 0x10100UL; // enable freeze (bit 16), freeze (bit 8)
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_BOX_CTL) < 0) {
    ERROR("cannot enable freeze of MC counters: %m\n");
    goto out;
  }

  int zero = 0x0UL; // Manually Reset Fixed Counter
   if (pwrite(pci_fd, &(zero), sizeof(zero), MC_A_FIXED_CTR) < 0 || pwrite(pci_fd, &(zero), sizeof(zero), MC_B_FIXED_CTR) < 0) {
     ERROR("cannot enable freeze of MC counter: %m\n");
     goto out;
   }

  ctl = 0x400000UL; // Enable Fixed Counter
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_FIXED_CTL) < 0) {
    ERROR("cannot undo reset of MC Fixed counter: %m\n");
    goto out;
  }

  /* Select Events for MC counters, MC_CTLx registers are 4 bits apart */
  int i;
  for (i = 0; i < nr_events; i++) {
    TRACE("PCI Address %08X, event %016lX\n", MC_CTL0 + 4*i, (unsigned long) events[i]);
    if (pwrite(pci_fd, &events[i], sizeof(events[i]), MC_CTL0 + 4*i) < 0) { 
      ERROR("cannot write event %016lX to PCI Address %08X through `%s': %m\n", 
            (unsigned long) events[i],
            (unsigned) MC_CTL0 + 4*i,
            pci_path);
      goto out;
    }
  }

  /* Manually reset programmable MC counters. They are 4 apart, but each counter register is split into 2 32-bit registers, A and B */
  for (i = 0; i < nr_events; i++) {
    if (pwrite(pci_fd, &zero, sizeof(zero), MC_A_CTR0 + 8*i) < 0 || 
	pwrite(pci_fd, &zero, sizeof(zero), MC_B_CTR0 + 8*i) < 0) { 
      ERROR("cannot reset counter %08X,%08X through `%s': %m\n", 
	    (unsigned) MC_A_CTR0 + 8*i, (unsigned) MC_B_CTR0 + 8*i,
            pci_path);
      goto out;
    }
  }

  ctl = 0x10000UL; // unfreeze counters
  if (pwrite(pci_fd, &ctl, sizeof(ctl), MC_BOX_CTL) < 0) {
    ERROR("cannot unfreeze MC counters: %m\n");
    goto out;
  }

  rc = 0;

 out:
  if (pci_fd >= 0)
    close(pci_fd);

  return rc;
}

static int intel_snb_imc_begin(struct stats_type *type)
{
  int nr = 0;
  
  uint32_t imc_events[4][4] = {
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_ALL,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_ALL,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_ALL,},
    { CAS_READS, CAS_WRITES, ACT_COUNT, PRE_COUNT_ALL,},
  };

  /* 2 buses and 4 devices per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[4] = {"10.0", "10.1", "10.4", "10.5"};


  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 4; j++) {
      char cpu[80];
      char bus_dev[80];
      snprintf(cpu, sizeof(cpu), "%d", i*8);
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      
      if (cpu_is_sandybridge(cpu)) // check that cpu 0 and 8 (sockets 0 and 1) are SNB      
	if (intel_snb_imc_begin_dev(bus_dev, imc_events[j], 4) == 0)
	  nr++; /* HARD */
    
    }
  }

  return nr > 0 ? 0 : -1;
}

static void intel_snb_imc_collect_box(struct stats_type *type, char *bus_dev)
{
  struct stats *stats = NULL;
  char pci_path[80];
  int pci_fd = -1;

  stats = get_current_stats(type, bus_dev);
  if (stats == NULL)
    goto out;

  TRACE("bus/dev %s\n", bus_dev);

  snprintf(pci_path, sizeof(pci_path), "/proc/bus/pci/%s", bus_dev);
  pci_fd = open(pci_path, O_RDONLY);
  if (pci_fd < 0) {
    ERROR("cannot open `%s': %m\n", pci_path);
    goto out;
  }
#define X(k,r...) \
  ({ \
    uint32_t val; \
    if ( pread(pci_fd, &val, sizeof(val), MC_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X) through `%s': %m\n", #k, MC_##k, pci_path); \
    else \
      stats_set(stats, #k, val);	\
  })
  CTL_KEYS;
#undef X

#define X(k,r...) \
  ({ \
    uint32_t val_a, val_b; \
    uint64_t val = 0x0ULL; \
    if ( pread(pci_fd, &val_a, sizeof(val_a), MC_A_##k) < 0 || pread(pci_fd, &val_b, sizeof(val_b), MC_B_##k) < 0 ) \
      ERROR("cannot read `%s' (%08X,%08X) through `%s': %m\n", #k, MC_A_##k, MC_B_##k, pci_path); \
    else \
      val = val_a; stats_set(stats, #k, (val<<32) + val_b);	\
  })
  CTR_KEYS;
#undef X

 out:
  if (pci_fd >= 0)
    close(pci_fd);
}

static void intel_snb_imc_collect(struct stats_type *type)
{
  /* 2 buses and 4 devices per bus */
  char *bus[2] = {"7f", "ff"};
  char *dev[4] = {"10.0", "10.1", "10.4", "10.5"};
  
  int i, j;
  for (i = 0; i < 2; i++) {
    for (j = 0; j < 4; j++) {
      char cpu[80];    
      char bus_dev[80];                                        
      snprintf(cpu, sizeof(cpu), "%d", i*8);
      snprintf(bus_dev, sizeof(bus_dev), "%s/%s", bus[i], dev[j]);
      
      if (cpu_is_sandybridge(cpu)) // check that cpu 0 and 8 (sockets 0 and 1) are SNB      
	intel_snb_imc_collect_box(type, bus_dev);
    }
  }
}

struct stats_type intel_snb_imc_stats_type = {
  .st_name = "intel_snb_imc",
  .st_begin = &intel_snb_imc_begin,
  .st_collect = &intel_snb_imc_collect,
#define X SCHEMA_DEF
  .st_schema_def = JOIN(KEYS),
#undef X
};
