#!/usr/bin/env bash
# In-image Codon FT pyext bake (pipeline_web.Dockerfile codon-build stage).
# Produces /opt/hpcperfstats/codon_parse with:
#   libhpcperfstats_codon_kernel.so  — Codon --lib (@export C entry)
#   hpcperfstats_codon_parse.so      — pyext_ft_init.c (Py_MOD_GIL_NOT_USED)
#   libcodonrt.so / libomp.so / libgfortran / libquadmath / libgcc_s
# linked with -Wl,-rpath,$ORIGIN (no /opt/codon at runtime).
set -euo pipefail

CODON_HOME="${CODON_HOME:-/opt/codon}"
CODON_SRC="${CODON_SRC:-/tmp/codon-src}"
CODON_OUT="${CODON_OUT:-/opt/hpcperfstats/codon_parse}"
CLANGXX="${CLANGXX:-$(command -v clang++-22 || command -v clang++ || true)}"
CLANGC="${CLANGC:-$(command -v clang-22 || command -v clang || true)}"

if [[ ! -x "${CODON_HOME}/bin/codon" ]]; then
  echo "missing_codon=${CODON_HOME}/bin/codon" >&2
  exit 1
fi
if [[ -z "${CLANGXX}" || -z "${CLANGC}" ]]; then
  echo "missing_clang_for_codon_pyext" >&2
  exit 1
fi
if [[ ! -f "${CODON_SRC}/feed_collapse_capi.py" || ! -f "${CODON_SRC}/pyext_ft_init.c" ]]; then
  echo "missing_codon_sources under ${CODON_SRC}" >&2
  exit 1
fi

mkdir -p "${CODON_OUT}" /opt/codon-shim
ln -sfn "${CLANGXX}" /opt/codon-shim/g++
# Codon --lib links zlib; prefer image zlib-ng when present.
if [[ -f /opt/zlib-ng/lib/libz.so ]]; then
  ln -sfn /opt/zlib-ng/lib/libz.so /usr/local/lib/libz.so
  echo /opt/zlib-ng/lib > /etc/ld.so.conf.d/zlib-ng.conf
  ldconfig 2>/dev/null || true
fi

export PATH="/opt/codon-shim:${CODON_HOME}/bin:${PATH}"
export LIBRARY_PATH="/opt/zlib-ng/lib:/usr/local/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="/opt/zlib-ng/lib:${CODON_HOME}/lib:${CODON_HOME}/lib/codon:/opt/python3.14t/lib:/opt/python3.14/lib:${LD_LIBRARY_PATH:-}"
export CODON_PYTHON=/opt/python3.14t/bin/python

echo "codon=$(codon --version)"
echo "ft314t=$(/opt/python3.14t/bin/python -V)"
echo "gil314=$(/opt/python3.14/bin/python3 -V)"
echo "codon_build_flags=--mcpu=native --linker-flags -flto=thin"

cd "${CODON_SRC}"
rm -f "${CODON_OUT}/libhpcperfstats_codon_kernel.so" \
  "${CODON_OUT}/hpcperfstats_codon_parse.so" \
  "${CODON_OUT}/pyext_ft_init.o"

if command -v clang >/dev/null 2>&1; then
  clang -march=native -mtune=native -### -xc /dev/null -fsyntax-only 2>&1 \
    | tr " " "\n" | grep -E "target-cpu|tune-cpu" | head -5 || true
fi

# Never pass --disable-native. Bake on the prod host (native CPU).
codon build -release --mcpu=native --linker-flags "-flto=thin" \
  --relocation-model=pic --lib \
  -o "${CODON_OUT}/libhpcperfstats_codon_kernel.so" \
  feed_collapse_capi.py

C_SYM="$(nm -D "${CODON_OUT}/libhpcperfstats_codon_kernel.so" | awk '/ feed_and_collapse_fingerprint_c$/ {print $3; exit}')"
PARSE_SYM="$(nm -D "${CODON_OUT}/libhpcperfstats_codon_kernel.so" | awk '/ parse_stats_lines_codon_run_c$/ {print $3; exit}')"
if [[ -z "${C_SYM}" ]]; then
  echo "missing_export feed_and_collapse_fingerprint_c" >&2
  nm -D "${CODON_OUT}/libhpcperfstats_codon_kernel.so" | head -40 >&2
  exit 1
fi
if [[ -z "${PARSE_SYM}" ]]; then
  echo "missing_export parse_stats_lines_codon_run_c" >&2
  nm -D "${CODON_OUT}/libhpcperfstats_codon_kernel.so" | head -40 >&2
  exit 1
fi
echo "c_export_sym=${C_SYM}"
echo "parse_export_sym=${PARSE_SYM}"

( objdump -d "${CODON_OUT}/libhpcperfstats_codon_kernel.so" 2>/dev/null || true ) \
  | grep -E "vadd|vmul|vmov|xmm|ymm|zmm" | head -5 \
  | sed "s/^/simd_insn_sample /" || echo "simd_insn_sample=none_or_unavailable"

"${CLANGC}" -fPIC -O2 -march=native -mtune=native -flto=thin \
  -I/opt/python3.14t/include/python3.14t \
  -c "${CODON_SRC}/pyext_ft_init.c" \
  -o "${CODON_OUT}/pyext_ft_init.o"

for _rt in libcodonrt.so libomp.so libgcc_s.so.1 libgfortran.so.5 libquadmath.so.0; do
  if [[ -f "${CODON_HOME}/lib/codon/${_rt}" ]]; then
    cp -a "${CODON_HOME}/lib/codon/${_rt}" "${CODON_OUT}/${_rt}"
  elif [[ -f "${CODON_HOME}/lib/${_rt}" ]]; then
    cp -a "${CODON_HOME}/lib/${_rt}" "${CODON_OUT}/${_rt}"
  else
    echo "missing_codon_runtime ${_rt}" >&2
    exit 1
  fi
done

g++ -Wno-unused-command-line-argument -flto=thin \
  "${CODON_OUT}/pyext_ft_init.o" -shared \
  -L"${CODON_OUT}" -lhpcperfstats_codon_kernel \
  -Wl,-rpath,'$ORIGIN' \
  -L"${CODON_OUT}" -lcodonrt -lomp \
  -L/opt/python3.14t/lib -Wl,-rpath,/opt/python3.14t/lib \
  -lpthread -ldl -lz -lm -lc \
  -o "${CODON_OUT}/hpcperfstats_codon_parse.so"

if ! command -v patchelf >/dev/null 2>&1; then
  echo "patchelf_required" >&2
  exit 1
fi
patchelf --set-rpath '$ORIGIN' "${CODON_OUT}/libhpcperfstats_codon_kernel.so"
patchelf --set-rpath '$ORIGIN:/opt/python3.14t/lib' "${CODON_OUT}/hpcperfstats_codon_parse.so"
rm -f "${CODON_OUT}/pyext_ft_init.o"

python3 -c "
import struct
d=open('${CODON_OUT}/hpcperfstats_codon_parse.so','rb').read(20)
t=struct.unpack_from('<H', d, 16)[0]
print('elf_type', t)
assert t==3, t
"
nm -D "${CODON_OUT}/hpcperfstats_codon_parse.so" \
  | grep -E "PyInit_hpcperfstats|feed_and_collapse_fingerprint_c|parse_stats_lines_codon_run_c" || true
readelf -d "${CODON_OUT}/hpcperfstats_codon_parse.so" | grep -E "NEEDED|RPATH|RUNPATH"
readelf -d "${CODON_OUT}/libhpcperfstats_codon_kernel.so" | grep -E "NEEDED|RPATH|RUNPATH"

echo "=== FT 3.14t import+fingerprint smoke (hard gate) ==="
# Fail-closed to image reality: no /opt/codon on LD_LIBRARY_PATH.
export PYTHONPATH="${CODON_OUT}:${CODON_SRC}"
export LD_LIBRARY_PATH="/opt/zlib-ng/lib:/opt/python3.14t/lib"
/opt/python3.14t/bin/python - <<'PY'
import math
import sys

import hpcperfstats_codon_parse as m
from feed_collapse import build_e6_payload_lines, feed_and_collapse_fingerprint as py_fp

assert hasattr(m, "feed_and_collapse_fingerprint")
assert hasattr(m, "parse_stats_lines_codon")
gil = sys._is_gil_enabled()
assert gil is False, gil
print("codon_pyext_314t_gil_off=pass")
fp = m.feed_and_collapse_fingerprint([])
assert fp == (0, 0, 0.0, 0.0), fp
print("fp_empty", fp)
empty_stats, empty_procs = m.parse_stats_lines_codon([])
assert empty_stats == [] and empty_procs == [], (empty_stats, empty_procs)

lines = build_e6_payload_lines(40)
codon_fp = m.feed_and_collapse_fingerprint(lines)
oracle_py = py_fp(lines)
assert codon_fp == oracle_py, (codon_fp, oracle_py)
print("fp_e6", codon_fp)

c_stats, c_procs = m.parse_stats_lines_codon(lines, 0)
assert len(c_stats) == codon_fp[0], (len(c_stats), codon_fp[0])
assert len(c_procs) == int(codon_fp[3]), (len(c_procs), codon_fp[3])
print("parse_stats_lines_codon_e6", len(c_stats), len(c_procs))
print("codon_pyext_314t_import=pass")
PY
echo "codon_pyext_314t=pass"

if /opt/python3.14/bin/python3 -c "
import hpcperfstats_codon_parse as m
assert m.feed_and_collapse_fingerprint([]) == (0, 0, 0.0, 0.0)
print('codon_pyext_gil=pass')
" 2>/dev/null; then
  echo "codon_pyext_gil=pass"
else
  echo "codon_pyext_gil=skip_ft_abi"
fi

ls -la "${CODON_OUT}"
echo "codon_out=${CODON_OUT}"

# cache-bust codon-ft-no-gil 20261022T050025Z
