#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "stats.h"

#include "host_mem_job.h"
#define X SCHEMA_DEF
static const char host_mem_job_schema_def[] = JOIN(KEYS);
#undef X
#undef KEYS

static void assert_present(const char *schema, const char *frag)
{
  assert(strstr(schema, frag) != NULL);
}

static void assert_absent(const char *schema, const char *frag)
{
  assert(strstr(schema, frag) == NULL);
}

int main(void)
{
  assert_present(host_mem_job_schema_def, " mem_used,U=KB");
  assert_present(host_mem_job_schema_def, " mem_peak,U=KB");
  assert_present(host_mem_job_schema_def, " anon_pages,U=KB");
  assert_present(host_mem_job_schema_def, " file_pages,U=KB");
  assert_present(host_mem_job_schema_def, " mapped,U=KB");
  assert_present(host_mem_job_schema_def, " dirty,U=KB");
  assert_present(host_mem_job_schema_def, " writeback,U=KB");
  assert_present(host_mem_job_schema_def, " page_tables,U=KB");
  /* Full host_mem KEYS must not appear (false parity). */
  assert_absent(host_mem_job_schema_def, "mem_total");
  assert_absent(host_mem_job_schema_def, "mem_free");
  assert_absent(host_mem_job_schema_def, "active");
  assert_absent(host_mem_job_schema_def, "slab");
  printf("test_host_mem_job_schema_contract passed\n");
  return 0;
}
