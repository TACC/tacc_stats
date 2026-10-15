#!/usr/bin/env bash
# Poll host full-PGO E2E log every 30 minutes; exit 0 on success, 1 on detectable failure.
set -euo pipefail

LOG="${HPC_PGO_E2E_LOG:-/data/HPCPerfStats/test_runs/full_pgo_e2e_hpcperfstats_dev_20261008.log}"
STATUS="${HPC_PGO_E2E_POLL_STATUS:-/data/HPCPerfStats/test_runs/full_pgo_e2e_poll_status.txt}"
INTERVAL="${HPC_PGO_E2E_POLL_SECONDS:-1800}"
WRAPPER_PID="${HPC_PGO_E2E_WRAPPER_PID:-}"

append_status() {
  echo "$(date -Is) $*" >>"${STATUS}"
}

current_run_log_slice() {
  local start_line=""
  start_line="$(rg -n '^(=== restart |=== --full-pgo start |=== resume soak)' "${LOG}" 2>/dev/null | tail -1 | cut -d: -f1 || true)"
  if [[ -z "${start_line}" ]]; then
    cat "${LOG}" 2>/dev/null || true
    return 0
  fi
  tail -n +"${start_line}" "${LOG}" 2>/dev/null || true
}

is_success() {
  current_run_log_slice | rg -q '^=== done ' 2>/dev/null
}

is_failure() {
  # set -x prints profile-guard helper names during a healthy build; match pgo_die output only.
  if current_run_log_slice | rg -q 'rebuild_full_site.sh: PGO FAILED|rebuild_full_site.sh: (abort|error|fatal)|Traceback \(most recent|Error: .*failed' 2>/dev/null; then
    return 0
  fi
  if [[ -n "${WRAPPER_PID}" ]] && ! kill -0 "${WRAPPER_PID}" 2>/dev/null; then
    if ! is_success; then
      return 0
    fi
  fi
  return 1
}

snapshot_phase() {
  rg -n '^(=== |rebuild_full_site.sh: podman build|pgo_soak:|=== --pgo-skip|=== done)' "${LOG}" 2>/dev/null | tail -5 || true
}

append_status "poll_loop start log=${LOG} interval=${INTERVAL}s wrapper_pid=${WRAPPER_PID:-none}"

while true; do
  lines="$(wc -l <"${LOG}" 2>/dev/null || echo 0)"
  phase="$(snapshot_phase | tr '\n' ' ')"
  append_status "tick lines=${lines} wrapper_alive=$([[ -n ${WRAPPER_PID} ]] && kill -0 ${WRAPPER_PID} 2>/dev/null && echo yes || echo no) phase=${phase}"

  if is_success; then
    append_status "RESULT SUCCESS"
    exit 0
  fi
  if is_failure; then
    append_status "RESULT FAILURE (see log tail)"
    tail -30 "${LOG}" >>"${STATUS}" 2>/dev/null || true
    exit 1
  fi
  sleep "${INTERVAL}"
done
