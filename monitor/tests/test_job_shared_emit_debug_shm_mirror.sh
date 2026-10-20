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
if ! grep -n 'insert_serialized(w, "-", NULL, NULL, 0)' "${SRC}" | grep -q .; then
  echo "expected insert_serialized(..., 0) for trailing multi-jid node-wide '-'" >&2
  exit 1
fi

# Idle path and jid inserts must still mirror (mirror_shm=1).
idle_mirrors="$(grep -c 'insert_serialized(w, "-", NULL, NULL, 1)' "${SRC}" || true)"
if test "${idle_mirrors}" -lt 1; then
  echo "expected idle '-' insert_serialized(..., 1) so empty discovery still updates shm" >&2
  exit 1
fi

jid_mirrors="$(grep -cE 'insert_serialized\(w, disc\.entries\[.*\].*, 1\)' "${SRC}" || true)"
if test "${jid_mirrors}" -lt 1; then
  echo "expected at least one jid insert_serialized(..., 1)" >&2
  exit 1
fi

echo "test_job_shared_emit_debug_shm_mirror passed"
