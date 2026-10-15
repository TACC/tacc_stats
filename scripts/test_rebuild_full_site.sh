#!/usr/bin/env bash
# Static regression for scripts/rebuild_full_site.sh (no compose required).
set -euo pipefail

: "${USER:?USER must identify the static-test account}"
: "${TMPDIR:=/data/user/${USER}/tmp}"
[[ "${TMPDIR}" == /data/* ]] || {
  echo "static rebuild tests require TMPDIR under /data" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FULL_SITE_SCRIPT="${SCRIPT_DIR}/rebuild_full_site.sh"
MEMORY_LIB="${SCRIPT_DIR}/lib/compose_pipeline_memory_high.sh"
RUNTIME_ADAPTER="${SCRIPT_DIR}/lib/podman_runtime.sh"
PGO_LIB="${SCRIPT_DIR}/pgo_lib.sh"

for path in "${FULL_SITE_SCRIPT}" "${MEMORY_LIB}" "${RUNTIME_ADAPTER}" "${PGO_LIB}"; do
  if [[ ! -f "${path}" ]]; then
    echo "missing ${path}" >&2
    exit 1
  fi
done

if ! bash -n "${FULL_SITE_SCRIPT}"; then
  echo "bash -n failed for rebuild_full_site.sh" >&2
  exit 1
fi
if ! bash -n "${MEMORY_LIB}"; then
  echo "bash -n failed for compose_pipeline_memory_high.sh" >&2
  exit 1
fi
if ! bash -n "${PGO_LIB}"; then
  echo "bash -n failed for pgo_lib.sh" >&2
  exit 1
fi

if ! grep -q 'podman_runtime.sh' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must source podman_runtime.sh" >&2
  exit 1
fi
if ! grep -q 'compose_pipeline_memory_high.sh' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must source compose_pipeline_memory_high.sh" >&2
  exit 1
fi
if ! grep -q 'pgo_lib.sh' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must source pgo_lib.sh" >&2
  exit 1
fi
if ! grep -q 'podman_runtime_require' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must call podman_runtime_require" >&2
  exit 1
fi
if grep -E '^[[:space:]]*apply_pipeline_memory_high([[:space:]]|\|)' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must keep apply_pipeline_memory_high commented out" >&2
  exit 1
fi
if ! grep -q '^[[:space:]]*#[[:space:]]*apply_pipeline_memory_high' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must retain a commented apply_pipeline_memory_high call" >&2
  exit 1
fi
if ! grep -q 'do not source' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must refuse being sourced (exit kills login shell)" >&2
  exit 1
fi
if ! grep -q '^read_pipeline_memory_max_bytes()' "${MEMORY_LIB}"; then
  echo "compose_pipeline_memory_high.sh must define read_pipeline_memory_max_bytes" >&2
  exit 1
fi

if grep -q 'build_musl_gcc_toolchain_image' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not build musl GCC toolchain image" >&2
  exit 1
fi
if ! grep -q 'pgo_prepare_host_pgroot_for_rebuild' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must prepare host PGOROOT via pgo_prepare_host_pgroot_for_rebuild" >&2
  exit 1
fi
if ! grep -q 'PGO_PHASE:-}" == stdlib' "${PGO_LIB}"; then
  echo "pgo_lib.sh must no-op pgo_prepare_host_pgroot_for_rebuild on stdlib" >&2
  exit 1
fi
if ! grep -q 'pgo_stdlib_empty_build_context_dir' "${PGO_LIB}"; then
  echo "pgo_lib.sh must use fixed empty dir for stdlib podman pgo context" >&2
  exit 1
fi
if grep -q 'run_cmd "${SCRIPT_DIR}/pgo_ensure_layout.sh"' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must run pgo_ensure_layout.sh outside run_cmd (dry-run must still mkdir PGOROOT)" >&2
  exit 1
fi
if ! grep -q 'pgo_ensure_pg_root' "${PGO_LIB}"; then
  echo "pgo_lib.sh must define pgo_ensure_pg_root for host PGOROOT bootstrap" >&2
  exit 1
fi
if ! grep -q 'pgo_chmod_shared_tree' "${PGO_LIB}"; then
  echo "pgo_lib.sh must define pgo_chmod_shared_tree for shared PGOROOT permissions" >&2
  exit 1
fi
if ! grep -q '! -perm 1777' "${PGO_LIB}"; then
  echo "pgo_chmod_shared_tree must only chmod directories that are not already 1777" >&2
  exit 1
fi
if ! grep -q 'pgo_podman_build_context_args "${REPO_ROOT}"' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must pass REPO_ROOT to pgo_podman_build_context_args" >&2
  exit 1
fi
if grep -q 'pgo_sketch_podman_context' "${PGO_LIB}"; then
  echo "pgo_lib.sh must not use retired sketch podman context paths" >&2
  exit 1
fi
if grep -q 'pgo_reset_sketch_tree' "${PGO_LIB}"; then
  echo "pgo_lib.sh must not define retired pgo_reset_sketch_tree" >&2
  exit 1
fi
if grep -q 'pgo_use_breadcrumb_path' "${PGO_LIB}"; then
  echo "pgo_lib.sh must not reference retired pgo_use_full_rebuild.done breadcrumb" >&2
  exit 1
fi
if ! grep -q 'run_compose_up_memory_high_and_summary' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must centralize compose up + memory.high" >&2
  exit 1
fi
if ! grep -q 'pgo_chmod_shared_tree' "${SCRIPT_DIR}/pgo_ensure_layout.sh"; then
  echo "pgo_ensure_layout.sh must call pgo_chmod_shared_tree" >&2
  exit 1
fi
if ! grep -q 'pgo_podman_build_context_args' "${PGO_LIB}"; then
  echo "pgo_lib.sh must define pgo_podman_build_context_args for Podman PGO mounts" >&2
  exit 1
fi
if ! grep -q -- '--volume=${root}:/root/.hpcperfstats_pgo:rw' "${PGO_LIB}"; then
  echo "pgo_lib.sh must podman build --volume the host PGOROOT (build-context binds do not persist)" >&2
  exit 1
fi
if ! grep -q 'compose_build_proxy_image' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must podman build proxy with --build-context=pgo=PGOROOT" >&2
  exit 1
fi
PROXY_DF="${REPO_ROOT}/services-conf/proxy.Dockerfile"
DB_DF="${REPO_ROOT}/services-conf/db.Dockerfile"
if ! grep -q 'BASH_ENV=/usr/local/lib/hpcperfstats/pgo_clang_flags.sh' "${PROXY_DF}"; then
  echo "proxy.Dockerfile must set BASH_ENV for pgo_clang_flags.sh under OCI (SHELL ignored)" >&2
  exit 1
fi
if ! grep -q '/bin/bash -o pipefail' "${PROXY_DF}"; then
  echo "proxy.Dockerfile must invoke /bin/bash for PGO build steps" >&2
  exit 1
fi
if ! grep -q 'BASH_ENV=/usr/local/lib/hpcperfstats/pgo_clang_flags.sh' "${DB_DF}"; then
  echo "db.Dockerfile must set BASH_ENV for pgo_clang_flags.sh under OCI (SHELL ignored)" >&2
  exit 1
fi
if ! grep -q '/bin/bash -o pipefail' "${DB_DF}"; then
  echo "db.Dockerfile must invoke /bin/bash for PGO build steps" >&2
  exit 1
fi
if ! grep -q 'compose_build_web_image' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must podman build web with --build-context=pgo=PGOROOT" >&2
  exit 1
fi
if ! grep -q 'pgo_podman_build_context_args' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must call pgo_podman_build_context_args for proxy/db podman build" >&2
  exit 1
fi
if ! grep -q 'pgo_image_build_cache_args' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must call pgo_image_build_cache_args for PGO image builds" >&2
  exit 1
fi
if ! grep -q 'mapfile -t cache_args.*pgo_image_build_cache_args' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must wire pgo_image_build_cache_args into podman/compose build" >&2
  exit 1
fi
PGO_LIB="${REPO_ROOT}/scripts/pgo_lib.sh"
if ! grep -q 'PGO_PHASE=use' "${PGO_LIB}" || ! grep -q '\-\-no-cache' "${PGO_LIB}"; then
  echo "pgo_lib.sh must emit --no-cache only for PGO_PHASE=use" >&2
  exit 1
fi
if ! grep -q '\-\-profile-phase' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must support --profile-phase" >&2
  exit 1
fi
if ! grep -q '^PGO_PHASE=stdlib' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must default PGO_PHASE=stdlib (no-arg rebuild)" >&2
  exit 1
fi
if ! grep -q '\-\-pgo-use' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must support --pgo-use" >&2
  exit 1
fi
if ! grep -q '\-\-pgo-skip' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must support --pgo-skip" >&2
  exit 1
fi
resolve_pgo_phase_body="$(awk '/^resolve_pgo_phase\(\) \{/,/^\}$/' "${FULL_SITE_SCRIPT}")"
if echo "${resolve_pgo_phase_body}" | grep -q 'profiles_ready'; then
  echo "resolve_pgo_phase must not auto-select use from profiles_ready" >&2
  exit 1
fi
if echo "${resolve_pgo_phase_body}" | grep -q 'pgo_use_breadcrumb'; then
  echo "resolve_pgo_phase must not auto-select skip from use breadcrumb" >&2
  exit 1
fi
partial_line="$(grep -n 'pgo_die_if_partial_profile_collection' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
resolve_line="$(grep -n '^  resolve_pgo_phase' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
if [[ -z "${partial_line}" || -z "${resolve_line}" || "${partial_line}" -le "${resolve_line}" ]]; then
  echo "rebuild_full_site.sh must run pgo_die_if_partial_profile_collection after resolve_pgo_phase" >&2
  exit 1
fi
if ! grep -q 'PGO_PHASE}" != stdlib' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must skip PGOROOT helpers when PGO_PHASE=stdlib" >&2
  exit 1
fi
if ! grep -q 'pgo_die' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must fail loud on PGO errors (pgo_die)" >&2
  exit 1
fi
if ! grep -q 'PODMAN_BUILD_STACK_IMAGES=(web proxy)' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must list podman build stack images (web proxy only)" >&2
  exit 1
fi
if grep -q 'build "${DEFAULT_BUILD_SERVICES' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not batch all stack services in one compose build" >&2
  exit 1
fi
if ! grep -q 'compose_build_web_image' "${FULL_SITE_SCRIPT}" \
  || ! grep -q 'compose_build_proxy_image' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must podman build web and proxy explicitly" >&2
  exit 1
fi
if grep -q 'podman-compose build' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not use podman-compose build (use podman build)" >&2
  exit 1
fi
if ! grep -q 'LAST_STEP=' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must track LAST_STEP for build failures" >&2
  exit 1
fi
if grep -qE '"\$\{PODMAN_COMPOSE\[@\]\}" up -d --build|"$\{PODMAN_COMPOSE\[@\]\}" up --build' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not pass --build to compose up" >&2
  exit 1
fi
if grep -qE '"\$\{PODMAN_COMPOSE\[@\]\}" up -d --force-recreate' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not use up -d --force-recreate (use down then up -d)" >&2
  exit 1
fi
if ! grep -q 'compose_down_project' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must define compose_down_project before up" >&2
  exit 1
fi
if ! grep -q 'pipeline_supervisor_shutdown.sh' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must source pipeline_supervisor_shutdown.sh" >&2
  exit 1
fi
HELPER="${SCRIPT_DIR}/lib/pipeline_supervisor_shutdown.sh"
if ! grep -q 'supervisorctl -c /home/hpcperfstats/services-conf/supervisord.conf shutdown' "${HELPER}"; then
  echo "pipeline_supervisor_shutdown.sh must run supervisorctl shutdown" >&2
  exit 1
fi
if grep -q 'supervisorctl .*>/dev/null || true' "${HELPER}" || grep -q 'shutdown || true' "${HELPER}"; then
  echo "pipeline_supervisor_shutdown.sh must not ignore supervisorctl failure" >&2
  exit 1
fi
if ! grep -q 'Shut down' "${HELPER}"; then
  echo "pipeline_supervisor_shutdown.sh must accept supervisorctl 'Shut down' when the socket closes" >&2
  exit 1
fi
shutdown_before_down="$(awk '
  /^compose_down_project\(\)/ { in_fn = 1 }
  in_fn && /pipeline_supervisor_shutdown$/ { call = NR }
  in_fn && /down --remove-orphans/ { down = NR; exit }
  END { if (call && down && call < down) print "yes" }
' "${FULL_SITE_SCRIPT}")"
if [[ "${shutdown_before_down}" != "yes" ]]; then
  echo "compose_down_project must call pipeline_supervisor_shutdown before down" >&2
  exit 1
fi
if grep -qE 'down -t "\$\{HPCPERFSTATS_COMPOSE_DOWN_TIMEOUT|down -t "\$\{timeout\}|down -t 30' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not pass down -t (overrides compose stop_grace_period)" >&2
  exit 1
fi
if ! grep -qF 'down --remove-orphans' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must run podman-compose down --remove-orphans before up" >&2
  exit 1
fi
if ! grep -q 'up -d --no-build' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must use up -d --no-build after explicit podman build" >&2
  exit 1
fi
if ! grep -q 'compose_ensure_local_stack_image_tags' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must tag local stack images before compose up" >&2
  exit 1
fi
if ! grep -q 'compose_ensure_local_stack_image_tags' "${PGO_LIB}"; then
  echo "pgo_lib.sh must define compose_ensure_local_stack_image_tags" >&2
  exit 1
fi
if grep -A8 'compose_ensure_local_stack_image_tags()' "${PGO_LIB}" | grep -q 'IFS= read -r canonical alias'; then
  echo "compose_ensure_local_stack_image_tags: IFS= read with two vars merges canonical+alias (use read -r canonical alias)" >&2
  exit 1
fi
if ! grep -q 'PG18_PROFILE=pg18-migrate' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must set pg18-migrate profile" >&2
  exit 1
fi
if ! grep -q 'compose_build_db_pg18' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must build db_pg18 via compose_build_db_pg18" >&2
  exit 1
fi
if ! grep -q 'compose_build_db_pg18' "${FULL_SITE_SCRIPT}" \
  || ! grep -q 'hpcperfstats-db' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must build db_pg18 image (hpcperfstats-db)" >&2
  exit 1
fi
if ! grep -qF -- '--profile "${PG18_PROFILE}" up -d --no-build' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must up stack with pg18-migrate profile (db_pg18 + default services)" >&2
  exit 1
fi
if grep -A10 'run_stack_up_and_verify()' "${FULL_SITE_SCRIPT}" | grep -q 'up_db_pg18'; then
  echo "run_stack_up_and_verify must not call up_db_pg18 twice (single profile up)" >&2
  exit 1
fi
if ! grep -q 'wait_for_compose_service_running' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must wait for services after up (web startup race)" >&2
  exit 1
fi
if ! grep -A6 'verify_default_stack_running()' "${FULL_SITE_SCRIPT}" | grep -q 'db rabbitmq'; then
  echo "verify_default_stack_running must require Hub db during PG18 dual-run migrate" >&2
  exit 1
fi
if ! grep -A8 'verify_default_stack_running()' "${FULL_SITE_SCRIPT}" | grep -q '"${PG18_SERVICE}"'; then
  echo "verify_default_stack_running must require db_pg18 during PG18 dual-run migrate" >&2
  exit 1
fi
if grep -qE '"\$\{PODMAN_COMPOSE\[@\]\}".*--force-recreate|run_cmd.*--force-recreate' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not pass --force-recreate to podman-compose" >&2
  exit 1
fi

build_line="$(grep -n 'compose_build_all_with_pgo' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
up_line="$(grep -n 'run_stack_up_and_verify' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
if [[ -z "${build_line}" || -z "${up_line}" ]]; then
  echo "rebuild_full_site.sh must define compose_build_all_with_pgo and run_stack_up_and_verify" >&2
  exit 1
fi
main_build="$(awk '/^main\(\)/ {m=1} m && /compose_build_all_with_pgo/ {print NR; exit}' "${FULL_SITE_SCRIPT}")"
main_up="$(awk '/^main\(\)/ {m=1} m && /run_compose_up_memory_high_and_summary/ {print NR; exit}' "${FULL_SITE_SCRIPT}")"
if [[ -z "${main_build}" || -z "${main_up}" ]]; then
  echo "rebuild_full_site.sh main must call compose_build_all_with_pgo and run_compose_up_memory_high_and_summary" >&2
  exit 1
fi
if grep -q 'prepare_profile_phase' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must not write unread profile_phase_started breadcrumb" >&2
  exit 1
fi
if ! grep -q '\-\-full-pgo' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must support --full-pgo" >&2
  exit 1
fi
if ! grep -q 'run_full_pgo_orchestration' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must define run_full_pgo_orchestration" >&2
  exit 1
fi
if ! grep -q 'pgo_run_soak_web_traffic' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must call pgo_run_soak_web_traffic during --full-pgo" >&2
  exit 1
fi
if ! grep -q 'pgo_soak_web_traffic.py' "${PGO_LIB}"; then
  echo "pgo_lib.sh must invoke pgo_soak_web_traffic.py" >&2
  exit 1
fi
if ! grep -q 'pgo_stop_stack_after_soak' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must define pgo_stop_stack_after_soak for post-soak down" >&2
  exit 1
fi
if ! awk '/^pgo_stop_stack_after_soak\(\)/,/^}/' "${FULL_SITE_SCRIPT}" | grep -q 'compose_down_project'; then
  echo "pgo_stop_stack_after_soak must call compose_down_project" >&2
  exit 1
fi
full_pgo_line="$(grep -n '\-\-full-pgo' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
orchestrator_line="$(grep -n 'run_full_pgo_orchestration' "${FULL_SITE_SCRIPT}" | head -n 1 | cut -d: -f1)"
main_full="$(awk '
  /^main\(\)/ {m=1; saw_full=0}
  m && /FULL_PGO/ && /-eq 1/ {saw_full=1}
  m && saw_full && /run_full_pgo_orchestration/ {print NR; exit}
' "${FULL_SITE_SCRIPT}")"
if [[ -z "${main_full}" ]]; then
  echo "rebuild_full_site.sh main must dispatch --full-pgo to run_full_pgo_orchestration" >&2
  exit 1
fi
if [[ -n "${full_pgo_line}" && -n "${orchestrator_line}" && "${orchestrator_line}" -le "${full_pgo_line}" ]]; then
  echo "run_full_pgo_orchestration should be defined after --full-pgo option parsing" >&2
  exit 1
fi
if ! grep -q 'only one of --profile-phase, --pgo-use, --pgo-skip, --full-pgo' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must mutual-exclude --full-pgo with other PGO flags" >&2
  exit 1
fi
SOAK_SCRIPT="${SCRIPT_DIR}/pgo_soak_web_traffic.py"
if [[ ! -f "${SOAK_SCRIPT}" ]]; then
  echo "missing ${SOAK_SCRIPT}" >&2
  exit 1
fi
if ! grep -q '=== PHASE soak starting ===' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must log === PHASE soak starting === before soak" >&2
  exit 1
fi
DETACHED="${SCRIPT_DIR}/run_pgo_e2e_detached.sh"
if ! grep -q 'E2E_WRAPPER_PID=' "${DETACHED}"; then
  echo "run_pgo_e2e_detached.sh must emit E2E_WRAPPER_PID=" >&2
  exit 1
fi
if ! grep -q 'setsid' "${DETACHED}"; then
  echo "run_pgo_e2e_detached.sh must detach with setsid" >&2
  exit 1
fi
POLL="${SCRIPT_DIR}/poll_full_pgo_e2e.sh"
if ! grep -q '=== resume soak' "${POLL}"; then
  echo "poll_full_pgo_e2e.sh current_run_log_slice must include === resume soak" >&2
  exit 1
fi
if ! grep -q 'rebuild_full_site.sh: PGO FAILED' "${POLL}"; then
  echo "poll_full_pgo_e2e.sh must treat rebuild_full_site.sh: PGO FAILED as failure" >&2
  exit 1
fi
if grep -q 'pgo_die_if_' "${POLL}"; then
  echo "poll_full_pgo_e2e.sh must not treat pgo_die_if_ helper traces as failure" >&2
  exit 1
fi
RESUME="${SCRIPT_DIR}/resume_pgo_soak_use_e2e_dev.sh"
if ! grep -q 'pgo_log_profile_gaps' "${RESUME}"; then
  echo "resume_pgo_soak_use_e2e_dev.sh must preflight with pgo_log_profile_gaps" >&2
  exit 1
fi
RESTART="${SCRIPT_DIR}/restart_full_pgo_e2e_dev.sh"
if ! grep -q 'PGOROOT=' "${RESTART}" || ! grep -q 'PGOROOT=' "${RESUME}"; then
  echo "dev E2E scripts must export PGOROOT so generate binds the compose pgo_profiles device" >&2
  exit 1
fi
assert_project_before_runtime_source() {
  local path="$1"
  local export_line source_line
  export_line="$(grep -n 'HPCPERFSTATS_COMPOSE_PROJECT:-hpcperfstats-dev' "${path}" | head -1 | cut -d: -f1)"
  source_line="$(grep -n 'scripts/lib/podman_runtime.sh' "${path}" | head -1 | cut -d: -f1)"
  if [[ -z "${export_line}" || -z "${source_line}" || "${export_line}" -gt "${source_line}" ]]; then
    echo "${path} must export HPCPERFSTATS_COMPOSE_PROJECT before sourcing podman_runtime.sh" >&2
    exit 1
  fi
}
assert_project_before_runtime_source "${RESTART}"
assert_project_before_runtime_source "${RESUME}"
restart_stop="$(grep -n 'podman stop -t 20' "${RESTART}" | head -1 | cut -d: -f1)"
restart_seed="$(grep -n 'pgo_soak_seed_rank0_job.py' "${RESTART}" | head -1 | cut -d: -f1)"
if [[ -z "${restart_stop}" || -z "${restart_seed}" || "${restart_stop}" -gt "${restart_seed}" ]]; then
  echo "restart_full_pgo_e2e_dev.sh must podman stop pipeline before seeding rank-0" >&2
  exit 1
fi
resume_stop="$(grep -n 'podman stop -t 20' "${RESUME}" | head -1 | cut -d: -f1)"
resume_seed="$(grep -n 'pgo_soak_seed_rank0_job.py' "${RESUME}" | head -1 | cut -d: -f1)"
if [[ -z "${resume_stop}" || -z "${resume_seed}" || "${resume_stop}" -gt "${resume_seed}" ]]; then
  echo "resume_pgo_soak_use_e2e_dev.sh must podman stop pipeline before seeding rank-0" >&2
  exit 1
fi
if ! awk '
  /run_pgo_soak_web_traffic\(\)/ { in_fn=1 }
  in_fn && /podman stop -t 20/ { saw_stop=1 }
  in_fn && /pgo_soak_seed_rank0_job.py/ { saw_seed=1 }
  in_fn && /^}/ { exit }
  END { exit !(saw_stop && saw_seed) }
' "${FULL_SITE_SCRIPT}"; then
  echo "run_pgo_soak_web_traffic must podman stop pipeline and re-seed rank-0" >&2
  exit 1
fi
if ! grep -q 'pgo_log_profile_gaps' "${PGO_LIB}"; then
  echo "pgo_lib.sh must define pgo_log_profile_gaps" >&2
  exit 1
fi
if ! grep -q 'run full --full-pgo generate first' "${PGO_LIB}"; then
  echo "pgo_log_profile_gaps must tell the operator to run full --full-pgo generate first" >&2
  exit 1
fi

up_default_body="$(awk '/^up_default_stack\(\)/ {u=1; next} u && /^}/ {exit} u' "${FULL_SITE_SCRIPT}")"
up_db_body="$(awk '/^up_db_pg18\(\)/ {u=1; next} u && /^}/ {exit} u' "${FULL_SITE_SCRIPT}")"
if grep -q 'podman build' <<<"${up_default_body}${up_db_body}"; then
  echo "rebuild_full_site.sh must not podman build inside up_* helpers" >&2
  exit 1
fi
if ! grep -q 'verify_default_stack_running' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must verify stack running after up" >&2
  exit 1
fi
if ! grep -qF 'starting podman-compose down + up' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must log before compose down + up" >&2
  exit 1
fi
if ! grep -q 'print_stack_summary' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must print stack summary (containers + network) after up" >&2
  exit 1
fi
if ! grep -q 'HPCPERFSTATS_NETWORK_NAME' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh stack summary must include compose network id" >&2
  exit 1
fi
if ! grep -q 'UP_COMPLETED=1' "${FULL_SITE_SCRIPT}"; then
  echo "rebuild_full_site.sh must set UP_COMPLETED after successful up" >&2
  exit 1
fi

# shellcheck source=lib/compose_pipeline_memory_high.sh
source "${MEMORY_LIB}"
high="$(compute_pipeline_memory_high_bytes 192000000000)"
want=$((192000000000 * 2 / 3))
if [[ "${high}" != "${want}" ]]; then
  echo "compute_pipeline_memory_high_bytes mismatch: got ${high}, want ${want}" >&2
  exit 1
fi

echo "test_rebuild_full_site.sh: all checks passed"
