#!/bin/bash
# Regression: multi-jid trailing node-wide '-' must not overwrite DEBUG shm.
# See job_shared_emit.c insert_serialized(..., mirror_shm).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/src/job_shared_emit.c"

test -f "${SRC}" || {
  echo "missing ${SRC}" >&2
  exit 1
}

# Trailing N>=2 node-wide insert must pass mirror_shm=0.
if ! grep -nE 'insert_serialized\(w, "-", NULL, NULL, 0,' "${SRC}" | grep -q .; then
  echo "expected insert_serialized(..., 0, ...) for trailing multi-jid node-wide '-'" >&2
  exit 1
fi

# Idle path and jid inserts must still mirror (mirror_shm=1).
idle_mirrors="$(grep -cE 'insert_serialized\(w, "-", NULL, NULL, 1,' "${SRC}" || true)"
if test "${idle_mirrors}" -lt 1; then
  echo "expected idle '-' insert_serialized(..., 1, ...) so empty discovery still updates shm" >&2
  exit 1
fi

jid_mirrors="$(grep -cE 'insert_serialized\(w, disc\.entries\[.*, 1,' "${SRC}" || true)"
if test "${jid_mirrors}" -lt 1; then
  echo "expected at least one jid insert_serialized(..., 1, ...)" >&2
  exit 1
fi

# Burst API must be wired so operators can see the full tick in *.burst.
grep -q 'stats_buffer_debug_shm_burst_begin' "${SRC}" \
  || {
    echo "job_shared_emit must call stats_buffer_debug_shm_burst_begin" >&2
    exit 1
  }
grep -q 'stats_buffer_debug_shm_burst_append' "${SRC}" \
  || {
    echo "job_shared_emit must call stats_buffer_debug_shm_burst_append" >&2
    exit 1
  }
grep -q 'stats_buffer_debug_shm_burst_commit' "${SRC}" \
  || {
    echo "job_shared_emit must call stats_buffer_debug_shm_burst_commit" >&2
    exit 1
  }

# |J|>=2 host '-' must emit unscheduled GPUs (remainder) and affinity-split CPUs.
grep -q 'job_gpu_set_diff' "${SRC}" \
  || {
    echo "job_shared_emit must compute GPU remainder via job_gpu_set_diff" >&2
    exit 1
  }
grep -q 'job_sched_affinity_remainder_cpulist' "${SRC}" \
  || {
    echo "job_shared_emit must compute CPU remainder via job_sched_affinity_remainder_cpulist" >&2
    exit 1
  }
grep -q 'is_cpu_type' "${SRC}" \
  || {
    echo "job_shared_emit must filter host_cpu/host_cpu_hw by affinity" >&2
    exit 1
  }

echo "test_job_shared_emit_debug_shm_mirror passed"
