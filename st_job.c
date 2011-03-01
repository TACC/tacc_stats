#define _GNU_SOURCE
#include "stats.h"
#include "trace.h"

int read_single(const char *path, unsigned long long *dest);

void read_jobid(void)
{
  struct stats *job_stats = NULL;
  unsigned long long jobid = 0;

  job_stats = get_current_stats(ST_JOB, NULL);
  if (job_stats == NULL) {
    ERROR("cannot get job_stats: %m\n");
    return;
  }

  read_single("/var/run/TACC_jobid", &jobid);

  stats_set(job_stats, "jobid", jobid);
}

struct stats_type ST_JOB_TYPE = {
  .st_name = "ST_JOB",
  .st_read = { &read_jobid, NULL, },
};
