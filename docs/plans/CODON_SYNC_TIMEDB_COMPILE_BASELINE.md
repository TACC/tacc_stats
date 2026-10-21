# Codon sync_timedb parse+collapse compile baseline

**Date:** 2026-10-21 (FT PyInit + C-ABI fingerprint)  
**Codon:** 0.20.4 under `/data/user/$USER/codon-0.20.4/`  
**Arm A interpreter:** `/opt/python3.14t/bin/python` (pipeline image)  
**Corpus:** `e6_dual_dev_v1` (dual-device `@full` cpu + host_proc)

## Class-free compile unit

`experiments/codon/sync_timedb_codon/feed_collapse.py` has **no** `class` definitions (schema = 4-tuple of lists; feed state = free functions; `HOST_PROC_KEYS` module-level). Required for Codon 0.20.4 pyext-era tooling (custom classes lack `__to_py__`).

`RUN_MAIN = False` by default so bench import does not auto-run; A/B / smoke scripts sed `RUN_MAIN = True` before `codon run` when Arm B is native Codon (not pyext).

C-ABI export lives in Codon-only `feed_collapse_capi.py` (`@export` + `str.from_ptr`) — not loaded under CPython unit tests.

## A/B performance (required gate)

| Field | Value |
|-------|-------|
| Log | see latest `test_runs/codon_ab_*.log` with `gate_1p25x=True` |
| Arm A | 3.14t `IncrementalStatsParser` + collapse |
| Arm B | Prefer pyext import under 3.14t when `HPCPERFSTATS_CODON_PYEXT_DIR` (or latest `test_runs/codon_pyext_out_*`) has both `.so` files; else `codon run` class-free `feed_collapse.py` |
| Pass | `gate_1p25x=True` (≥1.25×) |

## pyext build / import (FT hard gate)

Build: `experiments/codon/build_codon_ext_in_pipeline.sh`

1. `codon build --lib feed_collapse_capi.py` → `libhpcperfstats_codon_kernel.so` (`feed_and_collapse_fingerprint_c`).
2. Compile `pyext_ft_init.c` against `/opt/python3.14t` headers (multi-phase slots, `Py_MOD_GIL_USED`); link `hpcperfstats_codon_parse.so` with `-Wl,-rpath,$ORIGIN` + `-lhpcperfstats_codon_kernel`.
3. Hard smoke under **free-threaded** `/opt/python3.14t`: empty fingerprint `(0,0,0,0)` + E6 fingerprint vs CPython Incremental → **`codon_pyext_314t=pass`**.
4. GIL `/opt/python3.14` against the FT-header `.so` is best-effort (`codon_pyext_gil=pass` or `skip_ft_abi`).

Do **not** leave `hpcperfstats_codon_parse.py` stubs next to the `.so` (shadows the extension). Deploy **both** `.so` files on the same `PYTHONPATH` directory.

## Bridge

`hpcperfstats/dbload/lib/sync_timedb_codon_bridge.py` — fail-closed; `parse_stats_lines` only takes Codon when `parse_stats_lines_codon` exists (not shipped yet). Fingerprint API alone does not divert ORM ingest.

## Contract rule

`hpcperfstats/cursor-rules/codon-sync-timedb-parse-contract.mdc` — class-free unit + FT C-ABI/`Py_MOD_GIL_USED` + Codon-NumPy + A/B ≥1.25×.
