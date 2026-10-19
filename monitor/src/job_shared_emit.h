/* Shared-node multi-jid sample burst (one collect, N ring inserts). */
#ifndef JOB_SHARED_EMIT_H
#define JOB_SHARED_EMIT_H

struct sf_ring_buffer;

/*! Discover jids, evaluate full-resource fast path, emit 0/1/N payloads. */
void job_shared_emit_sample_burst(struct sf_ring_buffer *w);

/*! Conf knobs (defaults: step_id=0, pid_cap=4096, affinity_sample=8). */
extern int jid_require_step_id;
extern int jid_discover_pid_cap;
extern int affinity_pid_sample_limit;

#endif
