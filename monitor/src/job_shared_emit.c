/* One metrics collect + N serialized payloads for shared-node multi-jid. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "job_cgroup_mem.h"
#include "job_gpu_assign.h"
#include "job_proc_discover.h"
#include "job_sched_affinity.h"
#include "job_shared_emit.h"
#include "monitor_daemon.h"
#include "monitor_log.h"
#include "stats.h"
#include "stats_buffer.h"
#include "stats_buffer_debug_shm.h"
#include "stats_buffer_rows.h"
#include "stats_runtime.h"
#include "stats_text_format.h"

#if defined(MONITOR_HAVE_NVIDIA_GPU)
#include "nvidia_gpu_dcgm_watch.h"
#endif

struct emit_filter_ctx {
  const struct job_proc_jid_entry *entry; /* NULL = node-wide only (no proc/gpu) */
  const struct job_gpu_set *gpus;         /* NULL = no gpu filter (emit none for gpu types) */
  int include_node_wide;
  int include_proc;
  int include_gpu;
};

static int is_gpu_type(const char *st_name)
{
  return st_name != NULL && (strcmp(st_name, "nvidia_gpu") == 0 ||
                             strcmp(st_name, "amd_gpu") == 0 || strcmp(st_name, "intel_gpu") == 0);
}

static int is_proc_type(const char *st_name)
{
  return st_name != NULL && strcmp(st_name, "host_proc") == 0;
}

static int is_job_mem_type(const char *st_name)
{
  return st_name != NULL && strcmp(st_name, "host_mem_job") == 0;
}

static void populate_host_mem_job(const struct job_proc_discover_result *disc)
{
  struct stats_type *type;
  size_t i;

  if (disc == NULL)
    return;
  type = stats_type_get("host_mem_job");
  if (type == NULL || !type->st_enabled)
    return;
  for (i = 0; i < disc->n; i++) {
    struct job_cgroup_mem_kb kb;
    struct stats *st;
    char dev[2 + JOB_PROC_JID_MAX + 1];

    if (disc->entries[i].cgroup_relpath[0] == '\0')
      continue;
    if (job_cgroup_mem_read(disc->entries[i].cgroup_relpath, &kb) < 0)
      continue;
    if (job_cgroup_mem_format_dev(disc->entries[i].jid, dev, sizeof(dev)) < 0)
      continue;
    st = get_current_stats(type, dev);
    if (st == NULL)
      continue;
    stats_set(st, "mem_used", kb.mem_used);
    stats_set(st, "mem_peak", kb.mem_peak);
    stats_set(st, "anon_pages", kb.anon_pages);
    stats_set(st, "file_pages", kb.file_pages);
    stats_set(st, "mapped", kb.mapped);
    stats_set(st, "dirty", kb.dirty);
    stats_set(st, "writeback", kb.writeback);
    stats_set(st, "page_tables", kb.page_tables);
  }
}

static int proc_dev_pid(const char *dev, int *pid_out)
{
  /* host_proc device: name/pid/cmask/mmask */
  const char *slash;
  const char *p;
  char *end;
  long pid;

  if (dev == NULL)
    return -1;
  slash = strchr(dev, '/');
  if (slash == NULL)
    return -1;
  p = slash + 1;
  pid = strtol(p, &end, 10);
  if (end == p || (*end != '/' && *end != '\0'))
    return -1;
  *pid_out = (int)pid;
  return 0;
}

static int pid_in_entry(const struct job_proc_jid_entry *e, int pid)
{
  size_t i;

  if (e == NULL)
    return 0;
  for (i = 0; i < e->npids; i++) {
    if (e->pids[i] == pid)
      return 1;
  }
  return 0;
}

static int gpu_dev_in_set(const struct job_gpu_set *set, const char *dev)
{
  size_t i;

  if (set == NULL || dev == NULL)
    return 0;
  for (i = 0; i < set->n; i++) {
    if (strcmp(set->devs[i], dev) == 0)
      return 1;
  }
  return 0;
}

static int emit_row_filter(const char *st_name, const char *dev, void *ctx)
{
  struct emit_filter_ctx *c = ctx;

  if (c == NULL)
    return 1;
  if (is_proc_type(st_name)) {
    int pid;

    if (!c->include_proc || c->entry == NULL)
      return 0;
    if (proc_dev_pid(dev, &pid) < 0)
      return 0;
    return pid_in_entry(c->entry, pid);
  }
  if (is_gpu_type(st_name)) {
    if (!c->include_gpu)
      return 0;
    return gpu_dev_in_set(c->gpus, dev);
  }
  if (is_job_mem_type(st_name)) {
    if (c->entry == NULL)
      return 0; /* "-" / idle: omit all host_mem_job */
    return job_cgroup_mem_keep_dev(c->entry->jid, dev);
  }
  return c->include_node_wide ? 1 : 0;
}

static void fill_available_gpus(struct job_gpu_set *available)
{
  memset(available, 0, sizeof(*available));
#if defined(MONITOR_HAVE_NVIDIA_GPU)
  if (g_nvidia_gpu_runtime_ndev > 0) {
    int i;

    for (i = 0; i < g_nvidia_gpu_runtime_ndev && available->n < JOB_GPU_DEV_MAX; i++) {
      snprintf(available->devs[available->n], JOB_GPU_DEV_STR, "%d", i);
      available->n++;
    }
    available->inventory_known = 1;
    return;
  }
#endif
  /* Known-empty when NVIDIA GPU is compiled out or no devices are up. */
  available->inventory_known = 1;
}

static void format_jobs_csv(const struct job_proc_discover_result *disc, char *out, size_t out_cap)
{
  size_t i;
  size_t used = 0;

  out[0] = '\0';
  for (i = 0; i < disc->n; i++) {
    int pn = snprintf(out + used, out_cap - used, "%s%s", i ? "," : "", disc->entries[i].jid);

    if (pn < 0 || used + (size_t)pn >= out_cap) {
      out[0] = '\0';
      return;
    }
    used += (size_t)pn;
  }
}

/* mirror_shm: 0 = still ring-insert, but do not overwrite DEBUG fast/full (trailing
 * multi-jid node-wide '-' would otherwise hide the last jid sample in shm). */
static int insert_serialized(struct sf_ring_buffer *w, const char *hdr_jobid, const char *mark1,
                             const char *mark2, int mirror_shm)
{
  struct stats_buffer *sf;
  int rc;

  if (w == NULL)
    return -1;
  sf = monitor_daemon_alloc_stats_buffer();
  if (sf == NULL)
    return -1;
  snprintf(jobid, sizeof(jobid), "%s", hdr_jobid != NULL ? hdr_jobid : "-");
  if (mark1 != NULL)
    stats_buffer_mark(sf, "%s", mark1);
  if (mark2 != NULL)
    stats_buffer_mark(sf, "%s", mark2);
  w->b_count++;
  rc = stats_buffer_collect(sf);
  if (rc < 0) {
    stats_buffer_close(sf);
    free(sf);
    return -1;
  }
  if (mirror_shm && stats_buffer_debug_shm_sample_wanted(0, 1))
    stats_buffer_debug_shm_write_sample(sf, stats_buffer_payload_row_tier(sf));
  rc = ring_buffer_insert(sf, w, max_buffer_size, allow_ring_buffer_overwrite);
  if (rc < 0) {
    stats_buffer_close(sf);
    free(sf);
    return -1;
  }
  return 0;
}

void job_shared_emit_sample_burst(struct sf_ring_buffer *w)
{
  struct job_proc_discover_result disc;
  struct job_gpu_set available;
  struct timespec now;
  char jobs_csv[JOB_PROC_MAX_JIDS * (JOB_PROC_JID_MAX + 1)];
  size_t i;
  int full_resource = 0;

  memset(&disc, 0, sizeof(disc));
  if (job_proc_discover(&disc, jid_require_step_id, jid_discover_pid_cap) < 0) {
    /* fail-open: idle sample */
    disc.n = 0;
  }

  fill_available_gpus(&available);

  if (clock_gettime(CLOCK_REALTIME, &now) != 0) {
    now.tv_sec = 0;
    now.tv_nsec = 0;
  }
  stats_buffer_set_frozen_time(&now);

  /* One metrics collect for the whole burst (host_mem_job collect clears devices). */
  stats_runtime_collect_enabled_metrics(0);
  populate_host_mem_job(&disc);

  if (disc.n == 0) {
    struct emit_filter_ctx ctx = {.include_node_wide = 1, .include_proc = 0, .include_gpu = 0};

    stats_buffer_set_row_filter(emit_row_filter, &ctx);
    insert_serialized(w, "-", NULL, NULL, 1);
    stats_buffer_set_row_filter(NULL, NULL);
    stats_buffer_set_frozen_time(NULL);
    job_proc_discover_result_clear(&disc);
    return;
  }

  if (disc.n == 1) {
    struct job_gpu_set granted;
    struct job_gpu_set in_use;
    struct job_gpu_set g_union;
    char cpulist[512];
    enum job_cpu_coverage cov = JOB_CPU_UNKNOWN;

    job_gpu_assign_map_grant(disc.entries[0].job_gpus, &granted);
    job_gpu_assign_scan_fds(disc.entries[0].pids, disc.entries[0].npids, &in_use);
    job_gpu_set_union(&granted, &in_use, &g_union);
    (void)job_sched_affinity_union_cpulist(disc.entries[0].pids, disc.entries[0].npids,
                                           affinity_pid_sample_limit, cpulist, sizeof(cpulist),
                                           &cov);
    if (cov == JOB_CPU_EXACT_ALL && available.inventory_known &&
        job_gpu_set_exact_equal(&granted, &available))
      full_resource = 1;

    if (full_resource) {
      struct emit_filter_ctx ctx = {.entry = &disc.entries[0],
                                    .gpus = &g_union,
                                    .include_node_wide = 1,
                                    .include_proc = 1,
                                    .include_gpu = 1};

      stats_buffer_set_row_filter(emit_row_filter, &ctx);
      insert_serialized(w, disc.entries[0].jid, NULL, NULL, 1);
      stats_buffer_set_row_filter(NULL, NULL);
      stats_buffer_set_frozen_time(NULL);
      job_proc_discover_result_clear(&disc);
      return;
    }

    {
      char jobs_mark[256];
      char aff_mark[768];
      char gpus_wire[256];
      struct emit_filter_ctx ctx = {.entry = &disc.entries[0],
                                    .gpus = &g_union,
                                    .include_node_wide = 1,
                                    .include_proc = 1,
                                    .include_gpu = 1};

      format_jobs_csv(&disc, jobs_csv, sizeof(jobs_csv));
      snprintf(jobs_mark, sizeof(jobs_mark), "jobs jids=%s", jobs_csv);
      job_gpu_set_format_wire(&g_union, gpus_wire, sizeof(gpus_wire));
      if (cov != JOB_CPU_UNKNOWN && cpulist[0])
        snprintf(aff_mark, sizeof(aff_mark), "affinity jid=%s cpus=%s gpus=%s cg=sched",
                 disc.entries[0].jid, cpulist, gpus_wire);
      else
        aff_mark[0] = '\0';
      stats_buffer_set_row_filter(emit_row_filter, &ctx);
      insert_serialized(w, disc.entries[0].jid, jobs_mark, aff_mark[0] ? aff_mark : NULL, 1);
      stats_buffer_set_row_filter(NULL, NULL);
    }
    stats_buffer_set_frozen_time(NULL);
    job_proc_discover_result_clear(&disc);
    return;
  }

  /* N >= 2: per-jid payloads + one node-wide '-' payload. */
  format_jobs_csv(&disc, jobs_csv, sizeof(jobs_csv));
  for (i = 0; i < disc.n; i++) {
    struct job_gpu_set granted;
    struct job_gpu_set in_use;
    struct job_gpu_set g_union;
    char cpulist[512];
    char jobs_mark[256];
    char aff_mark[768];
    char gpus_wire[256];
    enum job_cpu_coverage cov = JOB_CPU_UNKNOWN;
    struct emit_filter_ctx ctx = {.entry = &disc.entries[i],
                                  .gpus = &g_union,
                                  .include_node_wide = 0,
                                  .include_proc = 1,
                                  .include_gpu = 1};

    job_gpu_assign_map_grant(disc.entries[i].job_gpus, &granted);
    job_gpu_assign_scan_fds(disc.entries[i].pids, disc.entries[i].npids, &in_use);
    job_gpu_set_union(&granted, &in_use, &g_union);
    (void)job_sched_affinity_union_cpulist(disc.entries[i].pids, disc.entries[i].npids,
                                           affinity_pid_sample_limit, cpulist, sizeof(cpulist),
                                           &cov);
    snprintf(jobs_mark, sizeof(jobs_mark), "jobs jids=%s", jobs_csv);
    job_gpu_set_format_wire(&g_union, gpus_wire, sizeof(gpus_wire));
    if (cov != JOB_CPU_UNKNOWN && cpulist[0])
      snprintf(aff_mark, sizeof(aff_mark), "affinity jid=%s cpus=%s gpus=%s cg=sched",
               disc.entries[i].jid, cpulist, gpus_wire);
    else
      aff_mark[0] = '\0';
    stats_buffer_set_row_filter(emit_row_filter, &ctx);
    insert_serialized(w, disc.entries[i].jid, jobs_mark, aff_mark[0] ? aff_mark : NULL, 1);
  }
  {
    struct emit_filter_ctx ctx = {.include_node_wide = 1, .include_proc = 0, .include_gpu = 0};

    stats_buffer_set_row_filter(emit_row_filter, &ctx);
    /* Do not mirror: would clobber last jid sample in DEBUG shm fast/full. */
    insert_serialized(w, "-", NULL, NULL, 0);
  }
  stats_buffer_set_row_filter(NULL, NULL);
  stats_buffer_set_frozen_time(NULL);
  job_proc_discover_result_clear(&disc);
}
