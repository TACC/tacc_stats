# Codon sync_timedb parse+collapse compile baseline

**Date:** 2026-10-21 (class-free pyext revision)  
**Codon:** 0.20.4 under `/data/user/$USER/codon-0.20.4/`  
**Arm A interpreter:** `/opt/python3.14t/bin/python` (pipeline image)  
**Corpus:** `e6_dual_dev_v1` (dual-device `@full` cpu + host_proc)

## Class-free compile unit

`experiments/codon/sync_timedb_codon/feed_collapse.py` has **no** `class` definitions (schema = 4-tuple of lists; feed state = free functions; `HOST_PROC_KEYS` module-level). Required for Codon 0.20.4 `-pyext` (custom classes lack `__to_py__`).

`RUN_MAIN = False` by default so pyext import does not auto-bench; A/B / smoke scripts sed `RUN_MAIN = True` before `codon run`.

## A/B performance (required gate)

| Field | Value |
|-------|-------|
| Log | see latest `test_runs/codon_ab_*.log` with `gate_1p25x=True` |
| Arm A | 3.14t `IncrementalStatsParser` + collapse |
| Arm B | `codon run` class-free `feed_collapse.py` |
| Pass | `gate_1p25x=True` (≥1.25×) |

## pyext build / import

Build: `experiments/codon/build_codon_ext_in_pipeline.sh`

1. `codon build --pyext` emits **ET_REL** object (Codon skips g++ link for `--pyext`).
2. Script post-links with the same flags as Codon `--lib` (`-shared -lcodonrt -lomp … -lz`) → **ET_DYN** `.so`.
3. **GIL** `/opt/python3.14` import + `feed_and_collapse_fingerprint([])` → `codon_pyext_gil=pass`.
4. **Free-threaded** `/opt/python3.14t` import currently **segfaults** in `PyInit_*` (`codon_pyext_314t=fail_ft_abi`). Production ingest stays fail-closed CPython on 3.14t until Codon/FT ABI is fixed.

Do **not** leave `hpcperfstats_codon_parse.py` stubs next to the `.so` (shadows the extension).

## Bridge

`hpcperfstats/dbload/lib/sync_timedb_codon_bridge.py` — fail-closed; `parse_stats_lines` only takes Codon when `parse_stats_lines_codon` exists (not shipped yet). Fingerprint API alone does not divert ORM ingest.

## Contract rule

`hpcperfstats/cursor-rules/codon-sync-timedb-parse-contract.mdc` — class-free pyext law + Codon-NumPy + A/B ≥1.25×.
