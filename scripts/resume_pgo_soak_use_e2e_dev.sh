#!/usr/bin/env bash
# After generate builds + stack up: soak → down → --pgo-use → --pgo-skip (dev ports + stubs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${HPC_PGO_E2E_LOG:-/data/HPCPerfStats/test_runs/full_pgo_e2e_hpcperfstats_dev_20261008.log}"
# podman_runtime.sh bakes PODMAN_COMPOSE from this value at source time.
export HPCPERFSTATS_COMPOSE_PROJECT="${HPCPERFSTATS_COMPOSE_PROJECT:-hpcperfstats-dev}"
# shellcheck source=lib/podman_runtime.sh
source "${ROOT}/scripts/lib/podman_runtime.sh"
# shellcheck source=pgo_lib.sh
source "${ROOT}/scripts/pgo_lib.sh"
export HPC_PGO_SOAK_SECONDS="${HPC_PGO_SOAK_SECONDS:-120}"
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

wait_web_gunicorn() {
  local attempt
  for attempt in $(seq 1 120); do
    if podman-compose -p "${HPCPERFSTATS_COMPOSE_PROJECT}" exec -T web python3 -c "
import urllib.error
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:8000/api/jobs/?limit=1', timeout=10)
except urllib.error.HTTPError as exc:
    if exc.code in (401, 403, 404, 302):
        pass
    else:
        raise
" >/dev/null 2>&1; then
      echo "web gunicorn ready after attempt=${attempt}"
      return 0
    fi
    sleep 5
  done
  echo "web gunicorn not ready after 600s" >&2
  return 1
}

cd "${ROOT}"
if ! pgo_log_profile_gaps "${ROOT}"; then
  echo "=== resume refused $(date -Is) ===" >>"${LOG}"
  exit 1
fi
{
  echo "=== resume soak→use $(date -Is) ==="
  wait_web_gunicorn
  podman kill "${HPCPERFSTATS_COMPOSE_PROJECT}_pipeline_1" >/dev/null 2>&1 || true
  podman stop -t 20 "${HPCPERFSTATS_COMPOSE_PROJECT}_pipeline_1" || true
  podman-compose -p "${HPCPERFSTATS_COMPOSE_PROJECT}" exec -T web python3 - < scripts/pgo_soak_seed_rank0_job.py
  pgo_run_soak_web_traffic "${ROOT}" \
    --repo-root "${ROOT}" \
    --compose-project "${HPCPERFSTATS_COMPOSE_PROJECT}" \
    --duration "${HPC_PGO_SOAK_SECONDS}"
  echo "=== resume post-soak down $(date -Is) ==="
  bash scripts/lib/pipeline_supervisor_shutdown.sh
  podman-compose -p "${HPCPERFSTATS_COMPOSE_PROJECT}" down --remove-orphans
  echo "=== --pgo-use $(date -Is) ==="
  ./scripts/rebuild_full_site.sh --pgo-use
  echo "=== --pgo-skip start $(date -Is) ==="
  ./scripts/rebuild_full_site.sh --pgo-skip
  echo "=== done $(date -Is) ==="
} >>"${LOG}" 2>&1
