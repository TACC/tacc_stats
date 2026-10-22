# Codon sync_timedb parse+collapse compile baseline

**Date:** 2026-10-21 (production divert: `parse_stats_lines_codon` + native ThinLTO)  
**Codon (prod):** 0.20.4 downloaded inside Dockerfile stage **`codon-build`** (sha256 pinned)  
**Codon (experiments only):** optional host tree `/data/user/$USER/codon-0.20.4/` for inventory / `codon run` spikes — **not** the prod bake path  
**Arm A interpreter:** `/opt/python3.14t/bin/python` (pipeline image)  
**Corpus:** `e6_dual_dev_v1` (dual-device `@full` cpu + host_proc)

## Class-free compile unit

`hpcperfstats/dbload/codon/feed_collapse.py` has **no** `class` definitions (schema = 4-tuple of lists; feed state = free functions; `HOST_PROC_KEYS` module-level). Required for Codon 0.20.4 pyext-era tooling (custom classes lack `__to_py__`).

`RUN_MAIN = False` by default so bench import does not auto-run; A/B / smoke scripts sed `RUN_MAIN = True` before `codon run` when Arm B is native Codon (not pyext).

C-ABI export lives in Codon-only `feed_collapse_capi.py` (`@export` + `str.from_ptr`) — not loaded under CPython unit tests. Extra kernel: `collapse_sum_kernel.py`.

## A/B performance (required gate)

| Field | Value |
|-------|-------|
| Log | `test_runs/codon_ab_20261021T185743.log` |
| Arm A | 3.14t `IncrementalStatsParser` + collapse (`arm_a_elapsed_s=2.144`) |
| Arm B | pyext (`arm_b_elapsed_s=0.469`, `arm_b_mode=pyext`) |
| Speedup | `ratio_a_over_b=4.574` |
| Pass | `gate_1p25x=True` (≥1.25×) |
| Note | CI on a weaker host understates Granite Rapids prod speedup; bake `.so` via in-Dockerfile `codon-build` on the prod host |
| SIMD evidence | `test_runs/codon_simd_objdump_*.log` — host E5-4650 shows SSE/AVX `vmov*`/`ymm` (`simd_opcode_hits=1502`); Granite Rapids prod bake expected to show AVX-512-class ops |

## pyext build / import (FT hard gate) — in-Dockerfile only

**Prod bake:** `services-conf/pipeline_web.Dockerfile` stage `codon-build` →
`hpcperfstats/dbload/codon/build_codon_ext.sh` → runtime
`COPY --from=codon-build` → `/opt/hpcperfstats/codon_parse`.

Forbidden for prod: host-side `build_codon_ext.sh`, staging `codon_parse_image/`,
or copying prebuilt `.so` into the build context.

1. `codon build -release --mcpu=native --linker-flags "-flto=thin" --lib feed_collapse_capi.py` → `libhpcperfstats_codon_kernel.so` (`feed_and_collapse_fingerprint_c`, `parse_stats_lines_codon_run_c`).
2. Compile `pyext_ft_init.c` with `-march=native -mtune=native -flto=thin` against `/opt/python3.14t` headers (multi-phase slots, **`Py_MOD_GIL_NOT_USED`**, per-slot marshal); link `hpcperfstats_codon_parse.so` with ThinLTO + `-Wl,-rpath,$ORIGIN` + `-lhpcperfstats_codon_kernel`.
3. Hard smoke under **free-threaded** `/opt/python3.14t`: **`sys._is_gil_enabled() is False`** after import (`codon_pyext_314t_gil_off=pass`) + empty fingerprint + E6 fingerprint + **`parse_stats_lines_codon`** row counts → **`codon_pyext_314t=pass`**.
4. GIL `/opt/python3.14` against the FT-header `.so` is best-effort (`codon_pyext_gil=pass` or `skip_ft_abi`).

Do **not** leave `hpcperfstats_codon_parse.py` stubs next to the `.so` (shadows the extension). Deploy pyext + kernel **and** Codon runtime libs (`libcodonrt.so`, `libomp.so`, `libgfortran.so.5`, `libquadmath.so.0`, `libgcc_s.so.1`) under `/opt/hpcperfstats/codon_parse` with `$ORIGIN` rpath (`PYTHONPATH` for `sync_timedb`). No `/opt/codon` mount in the pipeline image.

## Bridge

`hpcperfstats/dbload/lib/sync_timedb_codon_bridge.py` — fail-closed; width **`N = round(parse_pool × sync_codon_context_pool_fraction)`** (default 0.125). Production FT + baked `.so` uses **Popen stdio Codon workers** (`codon_mode=process_pool`, `codon_process_worker.py`, kill-only atexit — no `multiprocessing` teardown under FT) because codonrt is not safe across threads in one process; host fakes stay `codon_mode=in_process`. No process-wide serialize (`codonrt_serialize=0`). GIL-after-import fail-closed on 3.14t; `parse_stats_lines` takes Codon when `parse_stats_lines_codon` exists. Fingerprint API alone does not divert ORM ingest. Startup logs `codon_parse status=enabled|disabled … gil=off contexts=N codon_mode=… codonrt_serialize=0`. Concurrent stress: `test_runs/codon_stripe_stress_*.log` with `slot_occ_max>1`.

## Contract rule

`hpcperfstats/cursor-rules/codon-sync-timedb-parse-contract.mdc` — class-free unit + FT C-ABI/`Py_MOD_GIL_NOT_USED` + process-pool concurrent Codon + Codon-NumPy + A/B ≥1.25× + `--mcpu=native` / ThinLTO + GPU/`j:` feed parity.
