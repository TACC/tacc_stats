#!/usr/bin/env bash
# Detach the dev full-PGO E2E from the caller session (agent shells die on SIGHUP).
# Prints E2E_WRAPPER_PID= and appends the same line to the E2E log.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${HPC_PGO_E2E_LOG:-/data/HPCPerfStats/test_runs/full_pgo_e2e_hpcperfstats_dev_20261008.log}"
mkdir -p "$(dirname "${LOG}")"

if [[ "${HPC_PGO_E2E_DETACHED:-0}" == "1" ]]; then
  exec bash "${ROOT}/scripts/restart_full_pgo_e2e_dev.sh"
fi

export HPC_PGO_E2E_DETACHED=1
export HPC_PGO_E2E_LOG="${LOG}"
setsid nohup bash "$0" >>"${LOG}" 2>&1 </dev/null &
wrapper_pid=$!
echo "E2E_WRAPPER_PID=${wrapper_pid}" | tee -a "${LOG}"
