#define _GNU_SOURCE
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

// The performance monitor counters are used by software to count
// specific events that occur in the processor.  [The Performance
// Event Select Register (PERF_CTL[3:0])] MSRC001_00[03:00] and [The
// Performance Event Counter Registers (PERF_CTR[3:0])]
// MSRC001_00[07:04] specify the events to be monitored and how they
// are monitored.  All of the events are specified in section 3.14
// [Performance Counter Events].

#define AMD64_PERF_CTR_BASE 0xC0010004
#define AMD64_PERF_EVT_BASE 0xC0010000

// $ ls -l /dev/cpu/0
// total 0
// crw-------  1 root root 203, 0 Oct 28 18:47 cpuid
// crw-------  1 root root 202, 0 Oct 28 18:47 msr

// IA32_PMCx MSRs start at address 0C1H and occupy a contiguous block of MSR
// address space; the number of MSRs per logical processor is reported using
// CPUID.0AH:EAX[15:8].

// IA32_PERFEVTSELx MSRs start at address 186H and occupy a contiguous block
// of MSR address space. Each performance event select register is paired with a
// corresponding performance counter in the 0C1H address block.

#define IA32_PERF_CTR_BASE 0xC1
#define IA32_PERF_EVT_BASE 0x186

static int perf_access(char *cpu, int *nr_ctrs, unsigned *ctr_base, unsigned *evt_base)
{
  char cpuid_path[80];
  int cpuid_fd = -1;
  int rc = -1;

  /* Open /dev/cpuid/cpu/cpuid. */
  snprintf(cpuid_path, sizeof(cpuid_path), "/dev/cpu/%s/cpuid", cpu);
  cpuid_fd = open(cpuid_path, O_RDONLY);
  if (cpuid_fd < 0) {
    ERROR("cannot open `%s': %m\n", cpuid_path);
    goto out;
  }

  /* Get cpu vendor. */
  uint32_t buf[4];
  if (pread(cpuid_fd, buf, sizeof(buf), 0x0) < 0) {
    ERROR("cannot read cpu vendor through `%s': %m\n", cpuid_path);
    goto out;
  }
  buf[0] = buf[2], buf[2] = buf[3], buf[3] = buf[0];
  TRACE("vendor `%.12s'\n", (char*) buf + 4);

  if (strncmp((char*) buf + 4, "AuthenticAMD", 12) == 0) {
    *nr_ctrs = 4;
    *ctr_base = AMD64_PERF_CTR_BASE;
    *evt_base = AMD64_PERF_EVT_BASE;
    rc = 0;
    goto out;
  }

  if (strncmp((char*) buf + 4, "GenuineIntel", 12) != 0) {
    ERROR("unsupported cpu vendor `%.12s'\n", (char*) buf + 4);
    goto out; /* CentaurHauls? */
  }

  uint32_t eax;
  if (pread(cpuid_fd, &eax, sizeof(eax), 0x0A) < 0) {
    ERROR("cannot read `%s': %m\n", cpuid_path);
    goto out;
  }

  *nr_ctrs = (eax >> 8) & 0xff;
  *ctr_base = IA32_PERF_CTR_BASE;
  *evt_base = IA32_PERF_EVT_BASE;

 out:
  if (cpuid_fd >= 0)
    close(cpuid_fd);

  return rc;
}

static void collect_perf_cpu(struct stats_type *type, char *cpu)
{
  char msr_path[80];
  int msr_fd = -1;
  uint64_t *ctr_buf = NULL, *evt_buf = NULL;
  int nr_ctrs = -1;
  unsigned ctr_base, evt_base;

  if (perf_access(cpu, &nr_ctrs, &ctr_base, &evt_base) < 0)
    goto out;

  if (nr_ctrs <= 0)
    goto out;

  TRACE("cpu %s, nr_ctrs %d\n", cpu, nr_ctrs);

  ctr_buf = calloc(nr_ctrs, sizeof(*ctr_buf));
  evt_buf = calloc(nr_ctrs, sizeof(*evt_buf));
  if (ctr_buf == NULL || evt_buf == NULL) {
    ERROR("cannot allocate: %m\n");
    goto out;
  }

  /* Read MSRs. */
  snprintf(msr_path, sizeof(msr_path), "/dev/cpu/%s/msr", cpu);
  msr_fd = open(msr_path, O_RDONLY);
  if (msr_fd < 0) {
    ERROR("cannot open `%s': %m\n", msr_path);
    goto out;
  }

  if (pread(msr_fd, ctr_buf, nr_ctrs * sizeof(*ctr_buf), ctr_base) < 0) {
    ERROR("cannot read perf counters through `%s': %m\n", msr_path);
    goto out;
  }

  if (pread(msr_fd, evt_buf, nr_ctrs * sizeof(*evt_buf), evt_base) < 0) {
    ERROR("cannot read perf event select MSRs through `%s': %m\n", msr_path);
    goto out;
  }

  int i;
  for (i = 0; i < nr_ctrs; i++) {
    char id[80];
    struct stats *stats;

    snprintf(id, sizeof(id), "%s.%d", cpu, i); /* XXX */
    stats = get_current_stats(type, id);
    if (stats == NULL)
      continue;

    stats_set(stats, "ctr", ctr_buf[i]);
    stats_set(stats, "evt", evt_buf[i]);
  }

 out:
  if (msr_fd >= 0)
    close(msr_fd);
  free(ctr_buf);
  free(evt_buf);
}

static void collect_perf(struct stats_type *type)
{
  const char *path = "/dev/cpu";
  DIR *dir = NULL;

  dir = opendir(path);
  if (dir == NULL) {
    ERROR("cannot open `%s': %m\n", path);
    goto out;
  }

  struct dirent *ent;
  while ((ent = readdir(dir)) != NULL) {
    if (!isdigit(ent->d_name[0]))
      continue;
    collect_perf_cpu(type, ent->d_name);
  }

 out:
  if (dir != NULL)
    closedir(dir);
}

struct stats_type ST_PERF_TYPE = {
  .st_name = "ST_PERF",
  .st_collect = (void (*[])()) { &collect_perf, NULL, },
  .st_schema = (char *[]) { "ctr", "evt", NULL, },
};
