#!/usr/bin/env bash
# Native bake + optional Clang PGO flags for db/proxy/web image builds.
# Source from Dockerfile RUN; set PGO_PHASE / PGO_ROOT (or HPC_PGO_*) before calling.
set -euo pipefail

hpcperfstats_pgo_die() {
  echo "pgo_clang_flags: $*" >&2
  exit 1
}

hpcperfstats_pgo_phase() {
  printf '%s' "${HPC_PGO_PHASE:-${PGO_PHASE:-skip}}"
}

hpcperfstats_pgo_root() {
  printf '%s' "${HPC_PGO_ROOT:-${PGO_ROOT:-/root/.hpcperfstats_pgo}}"
}

hpcperfstats_pgo_ensure_raw_dir() {
  local namespace="${1:?namespace required}"
  local phase root raw
  phase="$(hpcperfstats_pgo_phase)"
  [[ "${phase}" == generate ]] || return 0
  root="$(hpcperfstats_pgo_root)"
  raw="${root}/${namespace}/raw"
  mkdir -p "${raw}"
  chmod 1777 "${raw}" 2>/dev/null || true
}

# One process writes one profraw. Compile-only RUNs never execute the library,
# and strip removes the profile runtime, so call this after install and before strip.
# Usage: hpcperfstats_pgo_capture_generate_exec NAMESPACE -- CMD... [--also NS...]
# No-op unless PGO_PHASE=generate (stdlib/use/skip rebuilds must not require a smoke).
hpcperfstats_pgo_capture_generate_exec() {
  local namespace="${1:?namespace required}"
  shift
  [[ "$(hpcperfstats_pgo_phase)" == generate ]] || return 0
  local -a cmd=() also=()
  local mode="cmd"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --also)
        mode="also"
        shift
        continue
        ;;
      --)
        shift
        continue
        ;;
    esac
    if [[ "${mode}" == "also" ]]; then
      also+=("$1")
    else
      cmd+=("$1")
    fi
    shift
  done
  [[ ${#cmd[@]} -gt 0 ]] || hpcperfstats_pgo_die "generate capture missing command for ${namespace}"
  hpcperfstats_pgo_ensure_raw_dir "${namespace}"
  local raw dest f src_file="" extra
  raw="$(hpcperfstats_pgo_root)/${namespace}/raw"
  dest="${raw}/smoke-%p.profraw"
  rm -f "${raw}"/smoke-*.profraw
  LLVM_PROFILE_FILE="${dest}" "${cmd[@]}" >/dev/null || true
  shopt -s nullglob
  for f in "${raw}"/*.profraw; do
    if [[ -s "${f}" ]]; then
      src_file="${f}"
      break
    fi
  done
  shopt -u nullglob
  [[ -n "${src_file}" ]] || hpcperfstats_pgo_die \
    "generate capture wrote no profraw for ${namespace} (${cmd[*]})"
  for extra in "${also[@]+"${also[@]}"}"; do
    [[ -n "${extra}" ]] || continue
    hpcperfstats_pgo_ensure_raw_dir "${extra}"
    cp -f "${src_file}" "$(hpcperfstats_pgo_root)/${extra}/raw/smoke.profraw"
  done
}

# jemalloc must be DT_NEEDED in an instrumented executable. dlopen after startup
# does not install its malloc hooks in time, and a non-instrumented driver has
# no profile runtime to dump the loaded library.
hpcperfstats_pgo_capture_generate_linked_malloc() {
  local namespace="${1:?namespace required}"
  local dir="${2:?directory required}"
  local libdir
  [[ "$(hpcperfstats_pgo_phase)" == generate ]] || return 0
  libdir="${dir}/lib"
  [[ -d "${libdir}" ]] || libdir="${dir}"
  cat > /tmp/hpc-pgo-malloc.c <<'EOF'
#include <stdlib.h>
int main(void) {
  void *p = malloc(128);
  if (!p) return 1;
  free(p);
  return 0;
}
EOF
  # CC on Alpine is "clang -fuse-ld=lld --ld-path=..."; quoting it is one argv.
  # shellcheck disable=SC2086
  ${CC:-clang} -fprofile-instr-generate -O0 -o /tmp/hpc-pgo-malloc /tmp/hpc-pgo-malloc.c \
    -L"${libdir}" -Wl,-rpath,"${libdir}" -ljemalloc \
    || hpcperfstats_pgo_die "generate capture failed to link jemalloc smoke for ${namespace}"
  hpcperfstats_pgo_capture_generate_exec "${namespace}" -- /tmp/hpc-pgo-malloc
}

hpcperfstats_pgo_capture_generate_dlopen() {
  local namespace="${1:?namespace required}"
  local dir="${2:?directory required}"
  shift 2
  [[ "$(hpcperfstats_pgo_phase)" == generate ]] || return 0
  if [[ "${namespace}" == *jemalloc ]]; then
    hpcperfstats_pgo_capture_generate_linked_malloc "${namespace}" "${dir}"
    return
  fi
  local so="" f
  shopt -s nullglob
  for f in "${dir}"/lib/lib*.so.* "${dir}"/lib/lib*.so "${dir}"/lib*.so.* "${dir}"/*.so; do
    [[ -f "${f}" ]] || continue
    so="${f}"
    break
  done
  shopt -u nullglob
  [[ -n "${so}" ]] || hpcperfstats_pgo_die "generate capture found no shared object under ${dir} for ${namespace}"
  cat > /tmp/hpc-pgo-dlopen.c <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char **argv) {
  int i;
  for (i = 1; i < argc; i++) {
    if (!dlopen(argv[i], RTLD_NOW | RTLD_GLOBAL)) {
      fprintf(stderr, "dlopen %s: %s\n", argv[i], dlerror());
      return 1;
    }
  }
  if (!fopen("/tmp/hpc-pgo-dlopen.ok", "w")) return 1;
  return 0;
}
EOF
  rm -f /tmp/hpc-pgo-dlopen.ok
  # shellcheck disable=SC2086
  ${CC:-clang} -fprofile-instr-generate -O0 -o /tmp/hpc-pgo-dlopen /tmp/hpc-pgo-dlopen.c -ldl \
    || ${CC:-clang} -fprofile-instr-generate -O0 -o /tmp/hpc-pgo-dlopen /tmp/hpc-pgo-dlopen.c \
    || hpcperfstats_pgo_die "generate capture failed to link dlopen smoke for ${namespace}"
  hpcperfstats_pgo_capture_generate_exec "${namespace}" -- /tmp/hpc-pgo-dlopen "${so}" "$@"
  [[ -f /tmp/hpc-pgo-dlopen.ok ]] || hpcperfstats_pgo_die \
    "generate capture dlopen failed for ${namespace} (${so})"
}

# timescaledb.so has unresolved postgres symbols, so dlopen outside the backend
# never registers counters. Start a throwaway postmaster (initdb refuses root).
hpcperfstats_pgo_capture_generate_postgres_extension() {
  local namespace="${1:?namespace required}"
  [[ "$(hpcperfstats_pgo_phase)" == generate ]] || return 0
  hpcperfstats_pgo_ensure_raw_dir "${namespace}"
  local raw pgdata f copied=0
  raw="$(hpcperfstats_pgo_root)/${namespace}/raw"
  pgdata=/tmp/hpc-pgo-pgdata
  rm -rf "${pgdata}"
  rm -f /tmp/hpc-pgo-pgext-*.profraw
  if ! id pgo >/dev/null 2>&1; then
    adduser -D -H -s /bin/sh pgo
  fi
  install -d -o pgo -g pgo -m 1777 /var/run/postgresql
  su pgo -c "/usr/local/bin/initdb -D '${pgdata}' --no-sync --auth=trust"
  # Postmaster uid cannot create files on the rootless PGOROOT volume.
  su pgo -c "export LLVM_PROFILE_FILE='/tmp/hpc-pgo-pgext-%p.profraw'; /usr/local/bin/pg_ctl -D '${pgdata}' -w start -o '-c shared_preload_libraries=timescaledb -c listen_addresses= -c unix_socket_directories=/var/run/postgresql'"
  su pgo -c "/usr/local/bin/pg_ctl -D '${pgdata}' -m fast -w stop"
  rm -rf "${pgdata}"
  shopt -s nullglob
  for f in /tmp/hpc-pgo-pgext-*.profraw; do
    if [[ -s "${f}" ]]; then
      cp -f "${f}" "${raw}/"
      copied=1
    fi
  done
  shopt -u nullglob
  [[ "${copied}" -eq 1 ]] || hpcperfstats_pgo_die \
    "generate capture wrote no profraw for ${namespace} (timescaledb preload)"
}

# Linking /opt/* built with PGO generate pulls instrumented deps (e.g. zstd→libz).
hpcperfstats_pgo_ensure_web_shared_link_dirs() {
  local ns
  for ns in web/shared/jemalloc web/shared/zlib-ng web/shared/zstd \
    web/shared/mpdecimal web/shared/libffi; do
    hpcperfstats_pgo_ensure_raw_dir "${ns}"
  done
}

hpcperfstats_pgo_ensure_web_gil_cpython_link_dirs() {
  hpcperfstats_pgo_ensure_web_shared_link_dirs
  hpcperfstats_pgo_ensure_raw_dir web/gil/cpython
}

hpcperfstats_pgo_ensure_web_ft_cpython_link_dirs() {
  hpcperfstats_pgo_ensure_web_shared_link_dirs
  hpcperfstats_pgo_ensure_raw_dir web/ft/cpython
}

hpcperfstats_pgo_ensure_web_gil_optimization_stack_link_dirs() {
  hpcperfstats_pgo_ensure_web_shared_link_dirs
  hpcperfstats_pgo_ensure_raw_dir web/gil/cpython
  hpcperfstats_pgo_ensure_raw_dir web/gil/optimization-stack
}

hpcperfstats_pgo_ensure_web_ft_optimization_stack_link_dirs() {
  hpcperfstats_pgo_ensure_web_shared_link_dirs
  hpcperfstats_pgo_ensure_raw_dir web/ft/cpython
  hpcperfstats_pgo_ensure_raw_dir web/ft/optimization-stack
}

hpcperfstats_pgo_ensure_db_zstd_upstream() {
  hpcperfstats_pgo_ensure_raw_dir db/lz4
  hpcperfstats_pgo_ensure_raw_dir db/zlib-ng
}

hpcperfstats_pgo_ensure_db_postgresql_link_dirs() {
  local ns
  for ns in db/jemalloc db/lz4 db/zlib-ng db/zstd db/icu db/liburing \
    db/postgresql; do
    hpcperfstats_pgo_ensure_raw_dir "${ns}"
  done
}

hpcperfstats_pgo_ensure_db_timescaledb_link_dirs() {
  hpcperfstats_pgo_ensure_db_postgresql_link_dirs
  hpcperfstats_pgo_ensure_raw_dir db/timescaledb
}

hpcperfstats_pgo_ensure_proxy_nginx_link_dirs() {
  local ns
  for ns in proxy/jemalloc proxy/nginx; do
    hpcperfstats_pgo_ensure_raw_dir "${ns}"
  done
}

# Shared libmpdec/jemalloc/libffi: ThinLTO link of a .so needs PIC on LTO objects.
hpcperfstats_shared_lib_namespace() {
  case "${1}" in
    */jemalloc | web/shared/libffi | web/shared/mpdecimal) return 0 ;;
    *) return 1 ;;
  esac
}

# Drop ThinLTO, linker plugin flags, and PGO from flags used at ./configure time.
hpcperfstats_strip_lto_and_pgo() {
  local s="${1}"
  printf '%s' "${s}" | sed -E \
    's/-flto=thin//g; s/-fuse-ld=lld//g; s/-fuse-ld=[^[:space:]]+//g; \
     s/--ld-path=[^[:space:]]+//g; \
     s/-fprofile-instr-generate=[^[:space:]]+//g; s/-fprofile-instr-use=[^[:space:]]+//g; \
     s/[[:space:]]+/ /g; s/^ //; s/ $//'
}

# variant: libs (Alpine default), pg (PostgreSQL vector width), debian-lib (Debian web
# native deps: ThinLTO in bake CFLAGS; --ld-path only via LDFLAGS / HPC_CLANG_LD_PATH).
hpcperfstats_native_base_cflags() {
  local variant="${1:-libs}"
  case "${variant}" in
    pg)
      printf '%s' "-O2 -march=native -mprefer-vector-width=512 -mtune=native -flto=thin --ld-path=$(hpcperfstats_alpine_ld_lld_path) -g0"
      ;;
    debian-lib)
      printf '%s' "-O2 -march=native -mtune=native -flto=thin -g0"
      ;;
    libs | *)
      printf '%s' "-O2 -march=native -mtune=native -flto=thin -g0"
      ;;
  esac
}

# Alpine lld22 installs ld.lld under /usr/bin (llvm-ar stays under /usr/lib/llvm22/bin).
hpcperfstats_alpine_ld_lld_path() {
  printf '%s' '/usr/bin/ld.lld'
}

# Autotools (jemalloc shared): compile uses bake CFLAGS (-flto=thin); link must repeat LTO.
hpcperfstats_alpine_thinlto_ldflags() {
  local lld flags
  lld="$(hpcperfstats_alpine_ld_lld_path)"
  # -fuse-ld=lld: clang++ must not fall back to musl gcc ld (TPOFF32 / ThinLTO .so link).
  flags="-flto=thin -fuse-ld=lld --ld-path=${lld}"
  # PGO generate: libclang_rt.profile.a needs libc when lld links .so (e.g. db/liburing).
  case "$(hpcperfstats_pgo_phase)" in
    generate) flags="${flags} -lc" ;;
  esac
  printf '%s' "${flags}"
}

# llvm-ar/ranlib/nm only (safe under BASH_ENV: do not rewrite CC — probe uses "${CC}" as argv0).
hpcperfstats_alpine_export_llvm_binutils() {
  local llvm_bin lto_ld
  llvm_bin="/usr/lib/llvm22/bin"
  lto_ld="$(hpcperfstats_alpine_thinlto_ldflags)"
  export AR="${llvm_bin}/llvm-ar"
  export RANLIB="${llvm_bin}/llvm-ranlib"
  export NM="${llvm_bin}/llvm-nm"
  export LLVM_CONFIG="${llvm_bin}/llvm-config"
  export HPC_THINLTO_LDFLAGS="${lto_ld}"
  export PATH="${llvm_bin}:${PATH}"
}

# Full autotools/cmake link: clang driver + lld (call from PGO RUN before make, not global bootstrap).
hpcperfstats_alpine_export_clang_link_toolchain() {
  local lld
  hpcperfstats_alpine_export_llvm_binutils
  lld="$(hpcperfstats_alpine_ld_lld_path)"
  export CC="clang -fuse-ld=lld --ld-path=${lld}"
  export CXX="clang++ -fuse-ld=lld --ld-path=${lld}"
}

# jemalloc DSO link must use lld (musl gcc ld rejects ThinLTO .pic.o); export before make.
hpcperfstats_alpine_jemalloc_export_link_toolchain() {
  hpcperfstats_alpine_export_clang_link_toolchain
  export LDFLAGS="${HPC_THINLTO_LDFLAGS}"
  export EXTRA_LDFLAGS="${HPC_THINLTO_LDFLAGS}"
}

hpcperfstats_alpine_maybe_bootstrap_llvm_toolchain() {
  [[ "${HPC_ALPINE_LLVM_TOOLCHAIN:-}" == 1 ]] || return 0
  hpcperfstats_alpine_export_llvm_binutils
}

hpcperfstats_alpine_maybe_bootstrap_llvm_toolchain

hpcperfstats_configure_cflags() {
  local namespace="${1:?namespace required}"
  local variant="${2:-libs}"
  local bake stripped
  bake="$(hpcperfstats_bake_cflags "${namespace}" "${variant}")"
  stripped="$(hpcperfstats_strip_lto_and_pgo "${bake}")"
  printf '%s' "${stripped}"
}

# CPython 3.14: --enable-optimizations + profile-gen-stamp / profile-run-stamp / profile-opt.
hpcperfstats_cpython_pgo_namespace() {
  case "${1}" in
    web/gil/cpython | web/ft/cpython) return 0 ;;
    *) return 1 ;;
  esac
}

# stdlib/generate/use (+ skip when merged profdata exists): --enable-optimizations.
hpcperfstats_namespace_default_profdata() {
  printf '%s' "$(hpcperfstats_pgo_root)/${1}/default.profdata"
}

hpcperfstats_pgroot_has_any_profile_artifact() {
  local root="${1:-$(hpcperfstats_pgo_root)}"
  [[ -d "${root}" ]] || return 1
  if find "${root}" \
    \( -name default.profdata -o -name '*.profraw' -o -name '*.profclangr' \) \
    -type f -size +0c -print -quit 2>/dev/null | grep -q .; then
    return 0
  fi
  return 1
}

hpcperfstats_pgo_die_if_skip_use_missing_profdata() {
  local namespace="${1:?namespace required}"
  local phase prof
  phase="$(hpcperfstats_pgo_phase)"
  prof="$(hpcperfstats_namespace_default_profdata "${namespace}")"
  case "${phase}" in
    use)
      [[ -s "${prof}" ]] \
        || hpcperfstats_pgo_die "PGO_PHASE=use requires non-empty ${prof}"
      ;;
    skip | "")
      if [[ -s "${prof}" ]]; then
        return 0
      fi
      if hpcperfstats_pgroot_has_any_profile_artifact; then
        hpcperfstats_pgo_die \
          "PGO_PHASE=${phase}: partial PGOROOT (missing ${prof}); refusing mixed compile"
      fi
      ;;
  esac
}

hpcperfstats_cpython_enable_optimizations_for_configure() {
  case "$(hpcperfstats_pgo_phase)" in
    stdlib | generate | use) printf '%s' '--enable-optimizations' ;;
    skip | "")
      if hpcperfstats_pgroot_has_any_profile_artifact; then
        printf '%s' '--enable-optimizations'
      fi
      ;;
  esac
}

# Live soak (Clang): LLVM_PROFILE_FILE → PGOROOT/.../raw/python-%p.profraw
# %p = PID so listend, sync_timedb, update_metrics, gunicorn workers each get a unique file;
# Upstream Makefile LLVM_PROF_MERGER merges $(pwd)/*.profclangr → code.profclangd before profile-opt.
hpcperfstats_cpython_llvm_profile_file() {
  local namespace="${1:?namespace required}"
  hpcperfstats_cpython_pgo_namespace "${namespace}" \
    || hpcperfstats_pgo_die "not a CPython PGO namespace: ${namespace}"
  printf '%s' "$(hpcperfstats_pgo_root)/${namespace}/raw/python-%p.profraw"
}

# Run $(LLVM_PROF_MERGER) from the configured CPython Makefile (same as profile-run-stamp tail).
hpcperfstats_cpython_run_makefile_prof_merger() {
  [[ -f Makefile ]] || hpcperfstats_pgo_die "CPython Makefile missing (run ./configure first)"
  make -s --eval '.PHONY: hpcperfstats-prof-merge' \
    --eval 'hpcperfstats-prof-merge: ; $(LLVM_PROF_MERGER)' \
    hpcperfstats-prof-merge
}

# Use-phase: copy soak profiles into $(pwd) as code-*.profclangr for upstream LLVM_PROF_MERGER.
hpcperfstats_cpython_stage_profiles_for_profile_opt() {
  local namespace="${1:?namespace required}"
  local root raw_dir prof staged=() f dest

  root="$(hpcperfstats_pgo_root)"
  raw_dir="${root}/${namespace}/raw"
  prof="${root}/${namespace}/default.profdata"

  rm -f ./code-*.profclangr ./code.profclangd

  shopt -s nullglob
  for f in "${raw_dir}"/python-*.profraw; do
    [[ -s "${f}" ]] || continue
    dest="./code-$(basename "${f}" .profraw).profclangr"
    cp "${f}" "${dest}"
    staged+=( "${dest}" )
  done
  for f in "${raw_dir}"/code-*.profclangr; do
    [[ -s "${f}" ]] || continue
    dest="./$(basename "${f}")"
    cp "${f}" "${dest}"
    staged+=( "${dest}" )
  done
  for f in "${raw_dir}"/*.profclangr; do
    [[ -s "${f}" ]] || continue
    case "$(basename "${f}")" in
      code-*.profclangr) continue ;;
    esac
    dest="./code-$(basename "${f}")"
    cp "${f}" "${dest}"
    staged+=( "${dest}" )
  done
  shopt -u nullglob

  if [[ ${#staged[@]} -gt 0 ]]; then
    hpcperfstats_cpython_run_makefile_prof_merger
  elif [[ -s "${prof}" ]]; then
    cp "${prof}" ./code.profclangd
  else
    hpcperfstats_pgo_die "PGO profile-opt requires raw profiles under ${raw_dir} or ${prof}"
  fi

  if [[ ! -s ./code.profclangd ]]; then
    hpcperfstats_pgo_die "PGO use: empty code.profclangd after merge"
  fi
}

# generate: install instrumented tree without running profile-opt (Makefile uses tabs after ':').
hpcperfstats_cpython_relax_install_deps_for_instrumented() {
  [[ -f Makefile ]] || hpcperfstats_pgo_die "CPython Makefile missing (run ./configure first)"
  sed -i \
    -e 's/^all:[[:space:]]*profile-opt/all: build_all/' \
    -e 's/^libinstall:[[:space:]]*all/libinstall: build_all/' \
    -e 's/^sharedinstall:[[:space:]]*all/sharedinstall: build_all/' \
    -e 's/^libainstall:[[:space:]]*all/libainstall: build_all/' \
    Makefile
  grep -q '^all:[[:space:]]*build_all' Makefile \
    || hpcperfstats_pgo_die "PGO generate: failed to repoint all: away from profile-opt"
  grep -q '^libinstall:[[:space:]]*build_all' Makefile \
    || hpcperfstats_pgo_die "PGO generate: failed to repoint libinstall: away from all"
}

# PGO generate must not run upstream profile-run-stamp (unittest) or profile-opt without soak data.
hpcperfstats_cpython_makefile_block_profile_opt_without_profclangd() {
  [[ -f Makefile ]] || hpcperfstats_pgo_die "CPython Makefile missing (run ./configure first)"
  cat >>Makefile <<'EOF'

.PHONY: hpcperfstats-block-profile-run-stamp hpcperfstats-profile-opt-guard
hpcperfstats-block-profile-run-stamp:
	@echo "pgo_clang_flags: profile-run-stamp blocked in PGO generate (use live soak, not unittest)" >&2
	@exit 1
hpcperfstats-profile-opt-guard:
	@test -s "$(CURDIR)/code.profclangd" || { echo "pgo_clang_flags: profile-opt requires non-empty code.profclangd (soak + merge/stage first)" >&2; exit 1; }
EOF
  if grep -q '^profile-run-stamp:' Makefile; then
    sed -i 's/^profile-run-stamp:[[:space:]]*/profile-run-stamp: hpcperfstats-block-profile-run-stamp /' Makefile
  fi
  if grep -q '^profile-opt:' Makefile; then
    sed -i 's/^profile-opt:[[:space:]]*/profile-opt: hpcperfstats-profile-opt-guard /' Makefile
  fi
}

hpcperfstats_cpython_make_install_profile_opt() {
  local namespace="${1:?namespace required}"
  local jobs="${2:-40}"

  hpcperfstats_cpython_stage_profiles_for_profile_opt "${namespace}"
  [[ -s ./code.profclangd ]] \
    || hpcperfstats_pgo_die "PGO profile-opt: refuse without code.profclangd"
  touch profile-run-stamp
  make -j"${jobs}" profile-opt
  make altinstall
}

# stdlib → plain make install. skip/use + merged profdata → profile-opt + altinstall.
# generate → profile-gen-stamp + altinstall.
hpcperfstats_cpython_make_install() {
  local namespace="${1:?namespace required}"
  local jobs="${2:-40}"
  local phase prof

  hpcperfstats_cpython_pgo_namespace "${namespace}" \
    || hpcperfstats_pgo_die "hpcperfstats_cpython_make_install: ${namespace}"

  phase="$(hpcperfstats_pgo_phase)"
  prof="$(hpcperfstats_namespace_default_profdata "${namespace}")"

  case "${phase}" in
    stdlib)
      make -j"${jobs}"
      make install
      ;;
    skip | "")
      hpcperfstats_pgo_die_if_skip_use_missing_profdata "${namespace}"
      if [[ -s "${prof}" ]]; then
        hpcperfstats_cpython_make_install_profile_opt "${namespace}" "${jobs}"
      else
        make -j"${jobs}"
        make install
      fi
      ;;
    generate)
      hpcperfstats_cpython_relax_install_deps_for_instrumented
      hpcperfstats_cpython_makefile_block_profile_opt_without_profclangd
      make -j"${jobs}" profile-gen-stamp
      make altinstall
      ;;
    use)
      hpcperfstats_cpython_make_install_profile_opt "${namespace}" "${jobs}"
      ;;
    *)
      hpcperfstats_pgo_die "unknown PGO_PHASE=${phase}"
      ;;
  esac
}

# variant: libs (default) or pg (PostgreSQL / Timescale extra vector width)
hpcperfstats_bake_cflags() {
  local namespace="${1:?namespace required}"
  local variant="${2:-libs}"
  local base phase root prof out

  base="$(hpcperfstats_native_base_cflags "${variant}")"

  if hpcperfstats_cpython_pgo_namespace "${namespace}"; then
    printf '%s' "${base}"
    return 0
  fi

  phase="$(hpcperfstats_pgo_phase)"
  root="$(hpcperfstats_pgo_root)"

  prof="$(hpcperfstats_namespace_default_profdata "${namespace}")"

  case "${phase}" in
    stdlib)
      out="${base}"
      ;;
    skip | "")
      hpcperfstats_pgo_die_if_skip_use_missing_profdata "${namespace}"
      if [[ -s "${prof}" ]]; then
        out="${base} -fprofile-instr-use=${prof}"
      else
        out="${base}"
      fi
      ;;
    generate)
      hpcperfstats_pgo_ensure_raw_dir "${namespace}"
      out="${base} -fprofile-instr-generate=${root}/${namespace}/raw/%m.profraw"
      ;;
    use)
      hpcperfstats_pgo_die_if_skip_use_missing_profdata "${namespace}"
      out="${base} -fprofile-instr-use=${prof}"
      ;;
    *)
      hpcperfstats_pgo_die "unknown PGO_PHASE=${phase}"
      ;;
  esac

  if hpcperfstats_shared_lib_namespace "${namespace}"; then
    out="${out} -fPIC"
  fi
  printf '%s' "${out}"
}
