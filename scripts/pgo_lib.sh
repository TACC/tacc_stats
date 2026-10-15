#!/usr/bin/env bash
# Shared PGO helpers for rebuild_full_site.sh (host-side).
set -euo pipefail

PGO_NAMESPACES_YAML="${PGO_NAMESPACES_YAML:-services-conf/pgo_namespaces.yaml}"

pgo_die() {
  echo "rebuild_full_site.sh: PGO FAILED: $*" >&2
  exit 1
}

pgo_root_dir() {
  printf '%s' "${PGOROOT:-${HPCPERFSTATS_PGO_ROOT:-/root/.hpcperfstats_pgo}}"
}

# Host PGOROOT must exist before compose bind mounts or Dockerfile RUN --mount=bind
# (device path in docker-compose.yaml). Idempotent; safe every rebuild.
pgo_ensure_pg_root() {
  local root
  root="$(pgo_root_dir)"
  if [[ -e "${root}" && ! -d "${root}" ]]; then
    pgo_die "PGOROOT exists but is not a directory: ${root}"
  fi
  if ! mkdir -p "${root}"; then
    pgo_die "cannot mkdir PGOROOT=${root} (permission denied?). Set PGOROOT to a writable path, e.g. /data/user/\$USER/hpcperfstats-pgo, and match pgo_profiles.device in docker-compose.yaml"
  fi
  if [[ ! -w "${root}" ]]; then
    pgo_die "PGOROOT not writable: ${root}"
  fi
}

# World-writable dirs (sticky) + world-readable/writable files so rootless builders,
# container UIDs, and merge/rebuild on different host users share one PGOROOT bind.
pgo_chmod_shared_tree() {
  local root
  root="$(pgo_root_dir)"
  [[ -d "${root}" ]] || return 0
  # Only fix modes that are wrong — avoid rewriting the whole tree (Podman pgo context digest).
  if [[ "$(stat -c '%a' "${root}" 2>/dev/null || echo "")" != "1777" ]]; then
    chmod 1777 "${root}" || pgo_die "chmod 1777 failed: ${root}"
  fi
  find "${root}" -type d ! -perm 1777 -exec chmod 1777 {} +
  find "${root}" -type f ! -perm -666 -exec chmod a+rw {} +
}

# FHS empty dir (stable Podman --build-context=pgo digest); never written by rebuild.
pgo_stdlib_empty_build_context_dir() {
  local d="${HPCPERFSTATS_PGO_EMPTY_BUILD_CONTEXT:-/usr/share/empty}"
  if [[ ! -d "${d}" ]]; then
    pgo_die \
      "stdlib podman build requires an existing empty directory for --build-context=pgo (set HPCPERFSTATS_PGO_EMPTY_BUILD_CONTEXT): ${d}"
  fi
  printf '%s' "${d}"
}

# Host PGOROOT tree for compose bind / generate / use / skip — not for stdlib builds.
pgo_prepare_host_pgroot_for_rebuild() {
  local _repo_root="${1:?repo_root}"
  local ensure_layout="${2:?ensure_layout script path}"
  [[ "${PGO_PHASE:-}" == stdlib ]] && return 0
  "${ensure_layout}"
}

pgo_stderr_why_full_pgroot_context() {
  local repo_root="${1:?repo_root}"
  local ns root
  root="$(pgo_root_dir)"
  case "${PGO_PHASE:-}" in
    skip) ;;
    *) return 0 ;;
  esac
  if ! pgo_tree_has_any_profile_data "${repo_root}"; then
    return 0
  fi
  echo "pgo podman build-context: using full PGOROOT — profile artifacts under ${root}:" >&2
  while IFS= read -r ns; do
    [[ -n "${ns}" ]] || continue
    if pgo_namespace_has_any_profile_artifact "${ns}" "${root}"; then
      echo "  - ${ns}" >&2
    fi
  done < <(pgo_list_namespaces "${repo_root}")
}

# Host PGOROOT for podman build. Additional --build-context bind mounts do not
# write back to the host directory (verified: touch inside from=pgo is gone
# after COMMIT). --volume is a real host bind and is what generate/use must use.
pgo_podman_build_context_args() {
  local repo_root="${1:?repo_root}"
  local root stub empty
  if [[ "${PGO_PHASE:-}" == stdlib ]]; then
    empty="$(pgo_stdlib_empty_build_context_dir)"
    echo "pgo podman build-context: stdlib empty ${empty} (no PGOROOT)" >&2
    printf '%s\n' "--build-context=pgo=${empty}"
    return 0
  fi
  root="$(cd "$(pgo_root_dir)" && pwd)"
  pgo_stderr_why_full_pgroot_context "${repo_root}"
  echo "pgo podman build-context: full PGOROOT ${root} (PGO_PHASE=${PGO_PHASE})" >&2
  printf '%s\n' "--build-context=pgo=${root}"
  printf '%s\n' "--volume=${root}:/root/.hpcperfstats_pgo:rw"
}

# PGO_PHASE=use must ignore stale layer cache (profile-opt flags); skip keeps cache.
pgo_image_build_cache_args() {
  if [[ "${PGO_PHASE:-}" == use ]]; then
    printf '%s\n' --no-cache
  fi
}

# After explicit podman build, compose up must not build/pull from a registry.
# Tag podman-compose fallback names ({project}_{service}) when include-merge drops image:.
compose_ensure_local_stack_image_tags() {
  local project canonical alias
  project="${HPCPERFSTATS_COMPOSE_PROJECT:-hpcperfstats}"
  while read -r canonical alias; do
    [[ -n "${canonical}" ]] || continue
    if ! podman image exists "${canonical}"; then
      pgo_die "stack image missing before compose up: ${canonical} (build images first)"
    fi
    if [[ "${canonical}" != "${alias}" ]] && ! podman image exists "${alias}"; then
      podman tag "${canonical}" "${alias}"
    fi
  done <<EOF
hpcperfstats:latest ${project}_web:latest
hpcperfstats:latest ${project}_pipeline:latest
hpcperfstats-proxy:latest ${project}_proxy:latest
hpcperfstats-db:latest ${project}_db_pg18:latest
EOF
}

pgo_use_failed_path() {
  printf '%s/breadcrumbs/pgo_use_full_rebuild.failed' "$(pgo_root_dir)"
}

pgo_list_namespaces() {
  local repo_root="${1:?repo_root}"
  local yaml_path="${repo_root}/${PGO_NAMESPACES_YAML}"
  grep -E '^[[:space:]]+- namespace:' "${yaml_path}" | sed -E 's/^[[:space:]]+- namespace:[[:space:]]*//'
}

pgo_namespace_has_nonempty_profdata() {
  local root ns
  root="$(pgo_root_dir)"
  ns="$1"
  [[ -s "${root}/${ns}/default.profdata" ]]
}

# Instrumentation profraw from PGO generate image builds (ignore zero-byte placeholders).
pgo_namespace_has_nonempty_instr_raw() {
  local root ns f
  root="$(pgo_root_dir)"
  ns="$1"
  shopt -s nullglob
  for f in "${root}/${ns}/raw/"*.profraw; do
    [[ -s "${f}" ]] && return 0
  done
  shopt -u nullglob
  return 1
}

# CPython use-phase needs live-soak profiles (not Makefile unittest output).
pgo_cpython_namespace_has_soak_raw() {
  local root ns f
  root="$(pgo_root_dir)"
  ns="$1"
  case "${ns}" in
    web/gil/cpython | web/ft/cpython) ;;
    *) return 1 ;;
  esac
  shopt -s nullglob
  for f in "${root}/${ns}/raw/"python-*.profraw "${root}/${ns}/raw/"code-*.profclangr; do
    [[ -s "${f}" ]] && return 0
  done
  for f in "${root}/${ns}/raw/"*.profclangr; do
    [[ -s "${f}" ]] && return 0
  done
  shopt -u nullglob
  return 1
}

pgo_namespace_profile_input_ready() {
  local ns="${1:?namespace}"
  if pgo_namespace_has_nonempty_profdata "${ns}"; then
    return 0
  fi
  case "${ns}" in
    web/gil/cpython | web/ft/cpython)
      pgo_cpython_namespace_has_soak_raw "${ns}"
      ;;
    *)
      pgo_namespace_has_nonempty_instr_raw "${ns}"
      ;;
  esac
}

# Any nonempty profile artifact under a namespace (ready or incomplete partial-PGOROOT detection).
pgo_namespace_has_any_profile_artifact() {
  local ns="${1:?namespace}"
  local root="${2:-$(pgo_root_dir)}"
  local f

  if [[ -s "${root}/${ns}/default.profdata" ]]; then
    return 0
  fi
  shopt -s nullglob
  for f in "${root}/${ns}/raw/"*.profraw "${root}/${ns}/raw/"*.profclangr; do
    [[ -s "${f}" ]] && return 0
  done
  shopt -u nullglob
  return 1
}

# Print build-time namespace gaps. Return 1 when resume cannot repair them.
# CPython soak gaps are omitted: resume soak can still write python-*.profraw.
pgo_log_profile_gaps() {
  local repo_root="${1:?repo_root}"
  local ns
  local -a gaps=()
  while IFS= read -r ns; do
    [[ -n "${ns}" ]] || continue
    case "${ns}" in
      web/gil/cpython | web/ft/cpython) continue ;;
    esac
    if pgo_namespace_profile_input_ready "${ns}"; then
      continue
    fi
    gaps+=( "$(pgo_namespace_use_gap_reason "${ns}")" )
  done < <(pgo_list_namespaces "${repo_root}")
  if [[ ${#gaps[@]} -eq 0 ]]; then
    return 0
  fi
  printf '%s\n' "${gaps[@]}" >&2
  echo "run full --full-pgo generate first; resume-only cannot fix build-time namespaces." >&2
  return 1
}

# True when every namespace can enter merge/use (merged profdata or soak-backed raw inputs).
profiles_ready() {
  local repo_root="${1:?repo_root}"
  local ns
  while IFS= read -r ns; do
    [[ -n "${ns}" ]] || continue
    if pgo_namespace_profile_input_ready "${ns}"; then
      continue
    fi
    return 1
  done < <(pgo_list_namespaces "${repo_root}")
  return 0
}

pgo_namespace_use_gap_reason() {
  local ns="${1:?namespace}"
  if pgo_namespace_profile_input_ready "${ns}"; then
    return 1
  fi
  case "${ns}" in
    web/gil/cpython | web/ft/cpython)
      printf '%s' \
        "${ns}: missing live soak (nonempty raw/python-*.profraw); check web/pipeline up, PGOROOT bind, LLVM_PROFILE_FILE"
      ;;
    *)
      printf '%s' \
        "${ns}: missing profiles (nonempty raw/*.profraw after --profile-phase generate, or default.profdata)"
      ;;
  esac
  return 0
}

# Stage-3-only PGOROOT (some raw/profdata, not all namespaces soak-ready): fail closed before compile.
pgo_die_if_partial_profile_collection() {
  local repo_root="${1:?repo_root}"
  local allow_profile_generate="${2:-0}"
  local ns
  local -a gaps=()

  if [[ "${allow_profile_generate}" -eq 1 ]]; then
    return 0
  fi
  if pgo_tree_sketch_only "${repo_root}" || profiles_ready "${repo_root}"; then
    return 0
  fi
  if ! pgo_tree_has_any_profile_data "${repo_root}"; then
    return 0
  fi

  while IFS= read -r ns; do
    [[ -n "${ns}" ]] || continue
    if pgo_namespace_profile_input_ready "${ns}"; then
      continue
    fi
    gaps+=( "$(pgo_namespace_use_gap_reason "${ns}")" )
  done < <(pgo_list_namespaces "${repo_root}")

  pgo_die \
    "PGO profile collection incomplete (soak or generate wiring not connected for every namespace); refusing compile. $(IFS='; '; echo "${gaps[*]}")"
}

pgo_tree_has_any_profile_data() {
  local repo_root="${1:?repo_root}" ns root
  root="$(pgo_root_dir)"
  while IFS= read -r ns; do
    [[ -n "${ns}" ]] || continue
    if pgo_namespace_has_any_profile_artifact "${ns}" "${root}"; then
      return 0
    fi
  done < <(pgo_list_namespaces "${repo_root}")
  return 1
}

# True when PGOROOT has no profile inputs in any namespace (layout-only / empty tree).
pgo_tree_sketch_only() {
  local repo_root="${1:?repo_root}"
  if pgo_tree_has_any_profile_data "${repo_root}"; then
    return 1
  fi
  return 0
}

# --profile-phase: remove all prior PGO artifacts (raw, profdata, breadcrumbs) and start clean.
pgo_wipe_pgroot_for_profile_phase() {
  local root
  root="$(pgo_root_dir)"
  pgo_ensure_pg_root
  shopt -s nullglob
  local entries=("${root}"/*)
  shopt -u nullglob
  if [[ ${#entries[@]} -eq 0 ]]; then
    echo "pgo_wipe_pgroot_for_profile_phase: PGOROOT already empty under ${root}" >&2
    return 0
  fi
  pgo_chmod_shared_tree
  find "${root}" -mindepth 1 -delete 2>/dev/null \
    || rm -rf "${root:?}"/*
  echo "pgo_wipe_pgroot_for_profile_phase: removed all contents under ${root}" >&2
}

# Wipe for --profile-phase; prompt when every namespace already has profile inputs (profiles_ready).
pgo_confirm_wipe_pgroot_for_profile_phase() {
  local repo_root="${1:?repo_root}"
  if ! profiles_ready "${repo_root}"; then
    pgo_wipe_pgroot_for_profile_phase
    return 0
  fi
  if [[ "${HPC_PGO_PROFILE_PHASE_FORCE_WIPE:-0}" == 1 ]]; then
    echo "pgo: HPC_PGO_PROFILE_PHASE_FORCE_WIPE=1; wiping complete profile set under $(pgo_root_dir)" >&2
    pgo_wipe_pgroot_for_profile_phase
    return 0
  fi
  if [[ ! -t 0 ]] || [[ ! -t 1 ]]; then
    pgo_die \
      "PGOROOT has a complete profile set (all namespaces profiles_ready); refusing --profile-phase wipe without a TTY. Re-run interactively and confirm, or set HPC_PGO_PROFILE_PHASE_FORCE_WIPE=1."
  fi
  echo "rebuild_full_site.sh: PGOROOT=$(pgo_root_dir) has profiles for all PGO namespaces (ready for merge/use)." >&2
  printf 'Delete ALL profile data under PGOROOT and restart PGO from scratch? [y/N] ' >&2
  local ans
  read -r ans
  case "${ans}" in
    y | Y | yes | YES)
      pgo_wipe_pgroot_for_profile_phase
      ;;
    *)
      pgo_die "profile-phase aborted: PGOROOT unchanged"
      ;;
  esac
}

pgo_print_summary() {
  local phase="$1"
  local crumb="absent"
  if [[ -f "$(pgo_use_failed_path)" ]]; then
    crumb="failed"
  fi
  echo "PGO phase=${phase} use_failed_marker=${crumb} PGOROOT=$(pgo_root_dir)" >&2
}

# Post-soak teardown hook for --full-pgo (implementation lives in rebuild_full_site.sh).
# rebuild_full_site.sh defines pgo_stop_stack_after_soak() → compose_down_project.

pgo_soak_python() {
  if [[ -n "${HPC_PGO_SOAK_PYTHON:-}" ]]; then
    printf '%s' "${HPC_PGO_SOAK_PYTHON}"
    return 0
  fi
  local ws_venv="/data/HPCPerfStats/.venv/bin/python3"
  if [[ -x "${ws_venv}" ]]; then
    printf '%s' "${ws_venv}"
    return 0
  fi
  command -v python3
}

pgo_soak_chromium_launch_ok() {
  local py="${1:?python}"
  "${py}" - <<'PY' >/dev/null 2>&1
from playwright.sync_api import sync_playwright

try:
  with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    browser.close()
except Exception:
  raise SystemExit(1)
PY
}

pgo_ensure_web_playwright() {
  local cid stamp=""
  cid="$("${PODMAN[@]}" ps \
    --filter "name=${HPCPERFSTATS_COMPOSE_PROJECT}_web" \
    --format '{{.ID}}' 2>/dev/null | head -1)"
  if [[ -n "${cid}" ]]; then
    stamp="${HPCPERFSTATS_HOST_CACHE:-/tmp}/pgo-web-playwright-${cid}.stamp"
  fi
  if [[ -n "${stamp}" && -f "${stamp}" ]]; then
    if "${PODMAN[@]}" exec "${cid}" python3 -c "import playwright" >/dev/null 2>&1; then
      return 0
    fi
    rm -f "${stamp}"
  fi
  echo "pgo_soak: installing Playwright + Chromium OS deps in web container..." >&2
  "${PODMAN_COMPOSE[@]}" exec -T web bash -lc \
    'python3 -m pip install -q "playwright>=1.63.0" && python3 -m playwright install --with-deps chromium'
  if [[ -n "${stamp}" ]]; then
    touch "${stamp}"
  fi
}

pgo_sync_soak_scripts_to_web() {
  local repo_root="${1:?repo_root}"
  local cid=""
  cid="$("${PODMAN[@]}" ps \
    --filter "name=${HPCPERFSTATS_COMPOSE_PROJECT}_web" \
    --format '{{.ID}}' 2>/dev/null | head -1)"
  if [[ -z "${cid}" ]]; then
    pgo_die "pgo_sync_soak_scripts_to_web: web service is not running"
  fi
  local script_name
  for script_name in \
    pgo_soak_web_traffic.py \
    pgo_soak_web_bootstrap.py \
    pgo_soak_discover_jobs.py; do
    podman cp "${repo_root}/scripts/${script_name}" \
      "${cid}:/home/hpcperfstats/scripts/${script_name}"
  done
}

pgo_web_container_proxy_ipv4() {
  local cid="${1:?web_container_id}"
  local proxy_ip=""
  proxy_ip="$("${PODMAN[@]}" exec "${cid}" getent ahostsv4 proxy.dns.podman 2>/dev/null \
    | awk '{print $1; exit}')"
  if [[ -z "${proxy_ip}" ]]; then
    proxy_ip="$("${PODMAN[@]}" exec "${cid}" getent ahostsv4 proxy 2>/dev/null \
      | awk '{print $1; exit}')"
  fi
  if [[ -z "${proxy_ip}" ]]; then
    pgo_die "pgo_web_container_proxy_ipv4: cannot resolve proxy from web container"
  fi
  printf '%s' "${proxy_ip}"
}

# Map INI server name → proxy on the web container loopback table so TLS SNI matches nginx.
pgo_soak_ensure_web_hosts_for_proxy() {
  local cid="${1:?web_container_id}"
  local proxy_ip="${2:?proxy_ip}"
  local server_line=""
  server_line="$("${PODMAN[@]}" exec "${cid}" python3 \
    /home/hpcperfstats/scripts/pgo_soak_web_bootstrap.py 2>/dev/null \
    | awk '/^\{/ {print; exit}')"
  if [[ -z "${server_line}" ]]; then
    pgo_die "pgo_soak_ensure_web_hosts_for_proxy: bootstrap JSON missing"
  fi
  local host_token=""
  host_token="$(HPC_PGO_SOAK_BOOTSTRAP_JSON="${server_line}" python3 - <<'PY'
import json, os
data = json.loads(os.environ["HPC_PGO_SOAK_BOOTSTRAP_JSON"])
server = (data.get("server") or "").split(",")[0].strip()
if "://" in server:
    from urllib.parse import urlparse
    server = urlparse(server).hostname or server
print(server)
PY
)"
  if [[ -z "${host_token}" ]]; then
    pgo_die "pgo_soak_ensure_web_hosts_for_proxy: empty server name from INI"
  fi
  "${PODMAN[@]}" exec "${cid}" sh -c \
    "grep -q '[[:space:]]${host_token}\$' /etc/hosts 2>/dev/null || echo '${proxy_ip} ${host_token}' >> /etc/hosts"
  printf 'https://%s' "${host_token}"
}

pgo_run_soak_web_traffic_in_web() {
  local repo_root="${1:?repo_root}"
  shift
  pgo_sync_soak_scripts_to_web "${repo_root}"
  pgo_ensure_web_playwright
  local cid proxy_ip proxy_base
  cid="$("${PODMAN[@]}" ps \
    --filter "name=${HPCPERFSTATS_COMPOSE_PROJECT}_web" \
    --format '{{.ID}}' 2>/dev/null | head -1)"
  proxy_ip="$(pgo_web_container_proxy_ipv4 "${cid}")"
  proxy_base="$(pgo_soak_ensure_web_hosts_for_proxy "${cid}" "${proxy_ip}")"
  local -a exec_env=(
    -e HPC_PGO_SOAK_IN_WEB=1
    -e "HPC_PGO_SOAK_BASE_URL=${proxy_base}"
  )
  if [[ -n "${HPC_PGO_SOAK_SECONDS:-}" ]]; then
    exec_env+=(-e "HPC_PGO_SOAK_SECONDS=${HPC_PGO_SOAK_SECONDS}")
  fi
  if [[ -n "${HPC_PGO_SOAK_ALLOW_METRICS_ONLY:-}" ]]; then
    exec_env+=(-e "HPC_PGO_SOAK_ALLOW_METRICS_ONLY=${HPC_PGO_SOAK_ALLOW_METRICS_ONLY}")
  fi
  "${PODMAN_COMPOSE[@]}" exec -T "${exec_env[@]}" web python3 \
    /home/hpcperfstats/scripts/pgo_soak_web_traffic.py "$@"
}

# Host Playwright when OS libs exist; otherwise soak inside running web (root + apt deps).
pgo_run_soak_web_traffic() {
  local repo_root="${1:?repo_root}"
  shift
  local py
  py="$(pgo_soak_python)"
  if [[ "${HPC_PGO_SOAK_FORCE_WEB:-0}" == "1" ]]; then
    pgo_run_soak_web_traffic_in_web "${repo_root}" "$@"
    return $?
  fi
  if pgo_soak_chromium_launch_ok "${py}"; then
    "${py}" "${repo_root}/scripts/pgo_soak_web_traffic.py" "$@"
    return $?
  fi
  echo "pgo_soak: host Chromium unavailable; using web container Playwright." >&2
  pgo_run_soak_web_traffic_in_web "${repo_root}" "$@"
}
