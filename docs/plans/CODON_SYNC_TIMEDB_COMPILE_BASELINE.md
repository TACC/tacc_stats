# Codon sync_timedb parse+collapse compile baseline

**Date:** 2026-10-21  
**Codon:** 0.20.4 under `/data/user/$USER/codon-0.20.4/`  
**Arm A interpreter:** `/opt/python3.14t/bin/python` (pipeline image)  
**Corpus:** `e6_dual_dev_v1` (dual-device `@full` cpu + host_proc)

## A/B performance (required gate)

| Field | Value |
|-------|-------|
| Log | `test_runs/codon_ab_20261021T101204.log` |
| reps / samples | 40 / 200 |
| `arm_a_elapsed_s` | 2.044759415 |
| `arm_b_elapsed_s` | 0.132221222 |
| `ratio_a_over_b` | **15.465** |
| `gate_1p25x` | **True** |
| Fingerprint | `collapsed_rows=1400`, `value_sum=1959300.0` (both arms) |

Arm A = production `IncrementalStatsParser` + `build_stats_dataframes` + `compute_deltas_and_arc` (includes `_collapse_stats_with_deltas`).  
Arm B = Codon-NumPy `feed_and_collapse` (`experiments/codon/sync_timedb_codon/feed_collapse.py`).

## Codon-NumPy smoke

`test_runs/codon_numpy_smoke_20261021T100454.log` — `codon_numpy_smoke=pass`.

## Compile inventory

`test_runs/codon_sync_timedb_inventory_20261021T101204.log` — `inventory_complete=true`, `inventory_pass=0`, `inventory_fail=42` (expected: Django/orchestrator/archive modules do not Codon-compile; hot path lives under `experiments/codon/sync_timedb_codon/`).

## Bridge

`hpcperfstats/dbload/lib/sync_timedb_codon_bridge.py` — fail-closed import of `hpcperfstats_codon_parse` pyext; `parse_stats_lines` tries Codon only when the extension exposes `parse_stats_lines_codon` (fingerprint-only builds keep CPython ingest).

## pyext vs `/opt/python3.14t`

- **Trivial pyext import proven:** `test_runs/codon_pyext_trivial_*.log` — `trivial_pyext_314t=pass` (`add(2,3)==5` under free-threaded 3.14.8).
- **Full `feed_collapse` pyext:** Codon 0.20.4 rejects exporting nested/`CompiledSchema` types (`__to_py__` / capture errors). Hot-path A/B uses `codon run` (Arm B). Production stays fail-closed CPython until a class-free pyext unit lands.

## Contract rule

`hpcperfstats/cursor-rules/codon-sync-timedb-parse-contract.mdc` — dual-registered in `agent-discipline-core.mdc` + `cursor-hooks/hook_task_router.py`.
