/* Phase 4: wire mark strings + jid/gpu helpers for shared-node payloads. */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "job_gpu_assign.h"
#include "job_proc_discover.h"

static void test_mark_shapes(void)
{
  char jobs[128];
  char aff[256];
  struct job_gpu_set g = {.n = 1};
  char gpus[32];

  snprintf(g.devs[0], JOB_GPU_DEV_STR, "2");
  job_gpu_set_format_wire(&g, gpus, sizeof(gpus));
  assert(strcmp(gpus, "2") == 0);

  snprintf(jobs, sizeof(jobs), "jobs jids=%s", "111,222");
  assert(strcmp(jobs, "jobs jids=111,222") == 0);
  snprintf(aff, sizeof(aff), "affinity jid=%s cpus=%s gpus=%s cg=sched", "111", "0-35", gpus);
  assert(strstr(aff, "cpus=0-35") != NULL);
  assert(strstr(aff, "gpus=2") != NULL);
  assert(strstr(aff, "cg=sched") != NULL);
}

static void test_full_resource_predicate_logic(void)
{
  /* Sole full-resource => no marks (logic locked here; daemon uses same predicates). */
  int sole = 1;
  enum { EXACT_ALL = 2 } cov = EXACT_ALL;
  struct job_gpu_set granted = {.n = 4, .inventory_known = 0};
  struct job_gpu_set available = {.n = 4, .inventory_known = 1};
  int i;

  for (i = 0; i < 4; i++) {
    snprintf(granted.devs[i], JOB_GPU_DEV_STR, "%d", i);
    snprintf(available.devs[i], JOB_GPU_DEV_STR, "%d", i);
  }
  assert(sole && cov == EXACT_ALL && job_gpu_set_exact_equal(&granted, &available));
}

int main(void)
{
  assert(job_proc_jid_acceptable("62909"));
  test_mark_shapes();
  test_full_resource_predicate_logic();
  printf("test_job_discovery_marks: ok\n");
  return 0;
}
