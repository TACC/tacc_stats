/* Read-only sched_getaffinity union for %affinity cpus= (shared-node build). */
#ifndef JOB_SCHED_AFFINITY_H
#define JOB_SCHED_AFFINITY_H

#include <sched.h>
#include <stddef.h>
#include <sys/types.h>

enum job_cpu_coverage { JOB_CPU_UNKNOWN = 0, JOB_CPU_PARTIAL = 1, JOB_CPU_EXACT_ALL = 2 };

/*! Inject for tests; NULL restores sched_getaffinity. Never mutate affinity masks. */
typedef int (*job_sched_affinity_get_fn)(pid_t pid, cpu_set_t *set, size_t setsize);
void job_sched_affinity_set_inject(job_sched_affinity_get_fn fn);

/*! Read /sys/devices/system/cpu/online into a CPU_ALLOC mask. Returns 0 on success. */
int job_sched_affinity_read_online(cpu_set_t **out_set, size_t *out_size, size_t *out_ncpus);

/*! Union affinity of up to sample_limit lowest pids; format Linux cpulist into out.
 *  Sets *cov to EXACT_ALL only when union equals online set. */
int job_sched_affinity_union_cpulist(const int *pids, size_t npids, int sample_limit, char *out,
                                     size_t out_cap, enum job_cpu_coverage *cov);

#endif
