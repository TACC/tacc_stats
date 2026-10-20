/* Phase 2: AutoDetect grant mapping + c122-018 minor permutation. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "job_gpu_assign.h"

/* c122-018: NVML index 0,1,2,3 -> minor 2,3,1,0 */
static int mock_nvml_index(int v)
{
  return v; /* identity field 52 */
}

static int mock_minor(int minor)
{
  static const int minor_to_i[] = {[0] = 3, [1] = 2, [2] = 0, [3] = 1};

  if (minor < 0 || minor > 3)
    return -1;
  return minor_to_i[minor];
}

static void write_gres(const char *path, const char *body)
{
  FILE *f = fopen(path, "we");

  assert(f != NULL);
  fputs(body, f);
  fclose(f);
}

static void test_nvml_grant_and_off(void)
{
  char gres[256];
  struct job_gpu_set granted;
  const char *tmpdir = getenv("TMPDIR");

  snprintf(gres, sizeof(gres), "%s/gres_XXXXXX", tmpdir && tmpdir[0] ? tmpdir : "/tmp");
  {
    int fd = mkstemp(gres);

    assert(fd >= 0);
    close(fd);
  }
  write_gres(gres, "AutoDetect=nvml\n");
  job_gpu_assign_set_gres_conf_path(gres);
  job_gpu_assign_reset_autodetect_cache();
  job_gpu_assign_set_nvml_hooks(mock_nvml_index, mock_minor);

  assert(job_gpu_assign_autodetect() == JOB_GPU_AD_NVML);
  assert(job_gpu_assign_map_grant("2", &granted) == 0);
  assert(granted.n == 1);
  assert(strcmp(granted.devs[0], "2") == 0);

  /* CUDA_VISIBLE_DEVICES must not be consulted — grant still 2 */
  setenv("CUDA_VISIBLE_DEVICES", "0", 1);
  assert(job_gpu_assign_map_grant("0,1,2,3", &granted) == 0);
  assert(granted.n == 4);

  write_gres(gres, "AutoDetect=off\n");
  job_gpu_assign_reset_autodetect_cache();
  assert(job_gpu_assign_map_grant("0,1,2,3", &granted) == 0);
  assert(granted.n == 0);

  unlink(gres);
}

static void test_set_diff(void)
{
  struct job_gpu_set avail = {.n = 0, .inventory_known = 1};
  struct job_gpu_set claimed = {.n = 0, .inventory_known = 0};
  struct job_gpu_set rem;

  snprintf(avail.devs[0], JOB_GPU_DEV_STR, "0");
  snprintf(avail.devs[1], JOB_GPU_DEV_STR, "1");
  snprintf(avail.devs[2], JOB_GPU_DEV_STR, "2");
  snprintf(avail.devs[3], JOB_GPU_DEV_STR, "3");
  avail.n = 4;
  snprintf(claimed.devs[0], JOB_GPU_DEV_STR, "0");
  snprintf(claimed.devs[1], JOB_GPU_DEV_STR, "1");
  snprintf(claimed.devs[2], JOB_GPU_DEV_STR, "2");
  claimed.n = 3;

  job_gpu_set_diff(&avail, &claimed, &rem);
  assert(rem.inventory_known == 1);
  assert(rem.n == 1);
  assert(strcmp(rem.devs[0], "3") == 0);

  job_gpu_set_diff(&avail, &avail, &rem);
  assert(rem.n == 0);
  assert(rem.inventory_known == 1);
}

static void test_wire_and_equal(void)
{
  struct job_gpu_set a = {.n = 0, .inventory_known = 1};
  struct job_gpu_set b = {.n = 0, .inventory_known = 1};
  char wire[64];

  snprintf(a.devs[0], JOB_GPU_DEV_STR, "0");
  snprintf(a.devs[1], JOB_GPU_DEV_STR, "1");
  a.n = 2;
  snprintf(b.devs[0], JOB_GPU_DEV_STR, "0");
  snprintf(b.devs[1], JOB_GPU_DEV_STR, "1");
  b.n = 2;
  assert(job_gpu_set_exact_equal(&a, &b));
  job_gpu_set_format_wire(&a, wire, sizeof(wire));
  assert(strcmp(wire, "0,1") == 0);
  job_gpu_set_format_wire(NULL, wire, sizeof(wire));
  assert(strcmp(wire, "-") == 0);
}

int main(void)
{
  test_nvml_grant_and_off();
  test_set_diff();
  test_wire_and_equal();
  printf("test_job_gpu_assign: ok\n");
  return 0;
}
