#!/usr/bin/env bash
# Re-run host full-PGO E2E on hpcperfstats-dev (append to log). Seed rank-0 first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${HPC_PGO_E2E_LOG:-/data/HPCPerfStats/test_runs/full_pgo_e2e_hpcperfstats_dev_20261008.log}"
# podman_runtime.sh bakes PODMAN_COMPOSE from this value at source time.
export HPCPERFSTATS_COMPOSE_PROJECT="${HPCPERFSTATS_COMPOSE_PROJECT:-hpcperfstats-dev}"
# shellcheck source=lib/podman_runtime.sh
source "${ROOT}/scripts/lib/podman_runtime.sh"
export HPC_PGO_SOAK_SECONDS="${HPC_PGO_SOAK_SECONDS:-120}"
export HPC_PGO_PROFILE_PHASE_FORCE_WIPE="${HPC_PGO_PROFILE_PHASE_FORCE_WIPE:-1}"
export HPCPERFSTATS_HTTP_PORT="${HPCPERFSTATS_HTTP_PORT:-8080}"
export HPCPERFSTATS_HTTPS_PORT="${HPCPERFSTATS_HTTPS_PORT:-8443}"
export HPCPERFSTATS_SYSLOG_PORT="${HPCPERFSTATS_SYSLOG_PORT:-1514}"
export HPCPERFSTATS_AMQP_PORT="${HPCPERFSTATS_AMQP_PORT:-5673}"
export PGOROOT="${PGOROOT:-/data/user/${USER}/hpcperfstats-pgo}"

STUB_ROOT="${HPCPERFSTATS_DEV_STUB_ROOT:-/data/HPCPerfStats/dev-compose-stubs}"
mkdir -p "${STUB_ROOT}/ssh" "${STUB_ROOT}/certs"
chmod 700 "${STUB_ROOT}/ssh"
if [[ ! -f "${STUB_ROOT}/certs/fullchain.pem" ]]; then
  cp -a "${ROOT}/tests/fixtures/proxy-ssl/"*.pem "${STUB_ROOT}/certs/"
fi

cd "${ROOT}"
{
  echo "=== restart $(date -Is) ==="
  echo "restart: ensuring stack is up (no build) before seed..." >&2
  # A killed `podman stop -t 480` can leave pipeline in state "stopping", which
  # makes the next up fail closed ("must be in Created or Stopped state").
  podman kill "${HPCPERFSTATS_COMPOSE_PROJECT}_pipeline_1" >/dev/null 2>&1 || true
  "${PODMAN_COMPOSE[@]}" up -d --no-build
  # update_metrics rewrites the seed row before this script can verify rank 0.
  # podman-compose stop uses -t 480 and can sit on a pipeline that is already exiting.
  podman stop -t 20 "${HPCPERFSTATS_COMPOSE_PROJECT}_pipeline_1" || true
  "${PODMAN_COMPOSE[@]}" exec -T web python3 - < scripts/pgo_soak_seed_rank0_job.py
  echo "=== --full-pgo start $(date -Is) HPC_PGO_SOAK_SECONDS=${HPC_PGO_SOAK_SECONDS} ==="
  ./scripts/rebuild_full_site.sh --full-pgo
  echo "=== --pgo-skip start $(date -Is) ==="
  ./scripts/rebuild_full_site.sh --pgo-skip
  echo "=== done $(date -Is) ==="
} >>"${LOG}" 2>&1
