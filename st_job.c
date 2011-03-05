#define _GNU_SOURCE
#include "stats.h"
#include "trace.h"
#include "collect.h"

static void collect_jobid(struct stats_type *type)
{
  struct stats *job_stats = NULL;
  unsigned long long jobid = 0;

  job_stats = get_current_stats(type, NULL);
  if (job_stats == NULL)
    return;

  collect_single(&jobid, "/var/run/TACC_jobid");

  stats_set(job_stats, "jobid", jobid);
}

struct stats_type ST_JOB_TYPE = {
  .st_name = "ST_JOB",
  .st_collect = &collect_jobid,
  .st_schema = (char *[]) { "jobid", NULL, },
};
