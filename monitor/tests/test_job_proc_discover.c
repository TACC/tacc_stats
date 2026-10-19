/* Phase 1: job_proc_discover fixtures (c122-018 cgroup shapes). */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "job_proc_discover.h"

static char g_root[256];

static void write_file(const char *path, const char *data)
{
  FILE *f = fopen(path, "we");

  assert(f != NULL);
  fputs(data, f);
  fclose(f);
}

static void mk_pid(int pid, uid_t uid, const char *cgroup, const char *environ_blob,
                   size_t environ_len)
{
  char dir[512];
  char path[512];
  char status[256];

  snprintf(dir, sizeof(dir), "%s/%d", g_root, pid);
  assert(mkdir(dir, 0755) == 0);
  snprintf(path, sizeof(path), "%s/cgroup", dir);
  write_file(path, cgroup);
  snprintf(path, sizeof(path), "%s/environ", dir);
  {
    FILE *f = fopen(path, "we");

    assert(f != NULL);
    if (environ_blob != NULL && environ_len > 0)
      fwrite(environ_blob, 1, environ_len, f);
    fclose(f);
  }
  snprintf(status, sizeof(status), "Name:\ttask\nUid:\t%u\t%u\t%u\t%u\n", uid, uid, uid, uid);
  snprintf(path, sizeof(path), "%s/status", dir);
  write_file(path, status);
  /* Filter uses st_uid of the process directory (stat). chown when permitted. */
  if (uid == 0 && geteuid() == 0)
    (void)chown(dir, 0, 0);
}

static void test_jid_acceptable(void)
{
  assert(job_proc_jid_acceptable("12345"));
  assert(!job_proc_jid_acceptable("0"));
  assert(!job_proc_jid_acceptable("-"));
  assert(!job_proc_jid_acceptable(""));
  assert(!job_proc_jid_acceptable("12 34"));
  assert(!job_proc_jid_acceptable("123456789012345678901234567890123")); /* 33 chars */
}

static void test_scope_token_grouping(void)
{
  struct job_proc_discover_result r;
  /* NUL-separated environ blobs (cannot use C string literals past first \\0). */
  static const char env1[] = {
      'S',  'L', 'U', 'R', 'M', '_', 'J', 'O', 'B', '_', 'I', 'D', '=', '6', '2', '8', '8', '8',
      '\0', 'S', 'L', 'U', 'R', 'M', '_', 'J', 'O', 'B', '_', 'G', 'P', 'U', 'S', '=', '0', '\0',
      'S',  'L', 'U', 'R', 'M', '_', 'S', 'T', 'E', 'P', '_', 'I', 'D', '=', '-', '5', '\0'};
  static const char env2[] = {
      'S',  'L', 'U', 'R', 'M', '_', 'J', 'O', 'B', '_', 'I', 'D', '=', '6', '2', '8', '9', '2',
      '\0', 'S', 'L', 'U', 'R', 'M', '_', 'J', 'O', 'B', '_', 'G', 'P', 'U', 'S', '=', '2', '\0',
      'S',  'L', 'U', 'R', 'M', '_', 'S', 'T', 'E', 'P', '_', 'I', 'D', '=', '-', '5', '\0'};
  static const char env3[] = {'S', 'L', 'U', 'R', 'M', '_', 'J', 'O', 'B', '_',
                              'I', 'D', '=', '9', '9', '9', '9', '9', '\0'};
  /* env-less sibling inherits token jid */
  const char *cg1 = "0::/system.slice/slurmstepd.scope/s4TDM5AXNE9900/step_batch/user/task_0\n";
  const char *cg1b =
      "0::/system.slice/slurmstepd.scope/s4TDM5AXNE9900/step_extern/user/task_special\n";
  const char *cg2 = "0::/system.slice/slurmstepd.scope/s4TDM5AXRQG500/step_batch/user/task_0\n";
  const char *cg_job_text =
      "0::/system.slice/slurmstepd.scope/other/job_33333/step_batch/user/task_0\n";

  assert(mkdir(g_root, 0755) == 0 || errno == EEXIST);
  setenv("HPCPERFSTATS_PROC_ROOT", g_root, 1);

  mk_pid(1001, 1000, cg1, env1, sizeof(env1));
  mk_pid(1002, 1000, cg1b, NULL, 0); /* inherits 62888 */
  mk_pid(2001, 1000, cg2, env2, sizeof(env2));
  mk_pid(3001, 1000, cg_job_text, env3, sizeof(env3));

  memset(&r, 0, sizeof(r));
  assert(job_proc_discover(&r, 0, 4096) == 0);
  assert(r.n == 3);
  assert(strcmp(r.entries[0].jid, "62888") == 0);
  assert(strcmp(r.entries[1].jid, "62892") == 0);
  assert(strcmp(r.entries[2].jid, "99999") == 0);
  assert(r.entries[0].npids >= 2);
  assert(strcmp(r.entries[0].job_gpus, "0") == 0);
  job_proc_discover_result_clear(&r);
}

static void test_rejects_root_and_bad_jid(void)
{
  struct job_proc_discover_result r;
  const char *cg = "0::/system.slice/slurmstepd.scope/tokA/step_batch/user/task_0\n";

  setenv("HPCPERFSTATS_PROC_ROOT", g_root, 1);
  /* Fresh root */
  snprintf(g_root, sizeof(g_root), "%s/proc_disc2_XXXXXX",
           getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp");
  assert(mkdtemp(g_root) != NULL);
  setenv("HPCPERFSTATS_PROC_ROOT", g_root, 1);

  {
    static const char bad[] = {'S', 'L', 'U', 'R', 'M', '_', 'J', 'O',
                               'B', '_', 'I', 'D', '=', '0', '\0'};
    static const char rootjid[] = {'S', 'L', 'U', 'R', 'M', '_', 'J', 'O',
                                   'B', '_', 'I', 'D', '=', '1', '\0'};

    mk_pid(4002, 1000, cg, bad, sizeof(bad)); /* bad jid rejected */
    if (geteuid() == 0)
      mk_pid(4001, 0, cg, rootjid, sizeof(rootjid)); /* uid 0 skipped by filter */
  }

  memset(&r, 0, sizeof(r));
  assert(job_proc_discover(&r, 0, 4096) == 0);
  assert(r.n == 0);
  job_proc_discover_result_clear(&r);
}

int main(void)
{
  const char *tmpdir = getenv("TMPDIR");

  snprintf(g_root, sizeof(g_root), "%s/proc_disc_XXXXXX", tmpdir && tmpdir[0] ? tmpdir : "/tmp");
  assert(mkdtemp(g_root) != NULL);

  test_jid_acceptable();
  test_scope_token_grouping();
  test_rejects_root_and_bad_jid();
  printf("test_job_proc_discover: ok\n");
  return 0;
}
