# Codon sync_timedb parse+collapse (0.20.4 + Codon-NumPy)

Compile the **parse+collapse numeric hot path** with Codon-NumPy; bridge into
CPython **3.14t** with fail-closed fallback. Django/orchestrator/archive stay
on `/opt/python3.14t` (`python-image-interpreter-contract.mdc`).

## Toolchain

- **Codon:** pinned **0.20.4** under `/data/user/$USER/codon-0.20.4/`
- **Linker:** PATH-shim `g++` → `clang++` in the pipeline image
- **Version file:** `VERSION`

```bash
mkdir -p /data/user/$USER/codon-0.20.4
curl -fsSL -o /tmp/codon-0.20.4.tar.gz \
  https://github.com/exaloop/codon/releases/download/v0.20.4/codon-linux-x86_64.tar.gz
tar -xzf /tmp/codon-0.20.4.tar.gz -C /data/user/$USER/codon-0.20.4 --strip-components=1
export CODON_HOME=/data/user/$USER/codon-0.20.4
$CODON_HOME/bin/codon --version
```

## Layout

| Path | Role |
|------|------|
| `sync_timedb_codon/feed_collapse.py` | Codon-NumPy feed + plain-host collapse |
| `run_codon_ab_baseline.sh` | **A/B** Arm A=3.14t Incremental+collapse vs Arm B=Codon |
| `run_sync_timedb_compile_inventory.sh` | Codon build attempt per `sync_timedb*.py` |
| `build_codon_ext_in_pipeline.sh` | pyext against `/opt/python3.14t` |
| `run_codon_vs_314t_container.sh` | Legacy feed-only microbench |
| `parse_kernel.py` / `e6_corpus.py` | CPython oracle / corpora |

## Gates

```bash
export CODON_HOME=/data/user/$USER/codon-0.20.4
./experiments/codon/run_sync_timedb_compile_inventory.sh
./experiments/codon/run_codon_ab_baseline.sh
./experiments/codon/build_codon_ext_in_pipeline.sh
```

A/B pass requires `gate_1p25x=True` in `test_runs/codon_ab_*.log`.
Baseline notes: `docs/plans/CODON_SYNC_TIMEDB_COMPILE_BASELINE.md`.

## Tests

```bash
/data/HPCPerfStats/.venv/bin/python3 -m pytest \
  hpcperfstats/tests/test_codon_parse_kernel_parity.py \
  hpcperfstats/tests/test_codon_collapse_parity.py \
  hpcperfstats/tests/test_sync_timedb_codon_bridge.py -q
```
