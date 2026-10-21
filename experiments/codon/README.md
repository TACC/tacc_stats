# Codon FT parse feasibility (phase 1)

Bounded feed kernel vs `IncrementalStatsParser` on E6 + fixture corpora.
**No** pipeline image or supervisord ABI changes. Native Codon timings run
**inside** `localhost/hpcperfstats:latest` (has `/opt/python3.14t`).

## Toolchain

- **Codon:** pinned **0.18.0** under `/data/user/$USER/codon/` (mounted into the container).
- **Linker:** Codon execs argv `g++`; container installs **Clang** and PATH-shims `g++` → `clang++` (no `g++` package).
- **Version file:** `VERSION`
- Install log: `test_runs/codon_install_*.log` (see plan todo).
- Baseline: `docs/plans/CODON_FEASIBILITY_BASELINE.md`

```bash
mkdir -p /data/user/$USER/codon
curl -fsSL -o /tmp/codon-linux-x86_64.tar.gz \
  https://github.com/exaloop/codon/releases/download/v0.18.0/codon-linux-x86_64.tar.gz
tar -xzf /tmp/codon-linux-x86_64.tar.gz -C /data/user/$USER/codon --strip-components=1
export PATH="/data/user/$USER/codon/bin:$PATH"
codon --version
```

## Layout

| Path | Role |
|------|------|
| `parse_kernel.py` | Bounded feed-only kernel (CPython oracle / parity) |
| `codon_native_e6_bench.py` | **Single-file Codon compile unit** + native microbench |
| `e6_corpus.py` | E6 synthetic corpus + host_proc @full fixture excerpt |
| `bench_cpython.py` | CPython timing: `IncrementalStatsParser` vs `FeedKernel` |
| `bench_driver.py` | Legacy multi-module Codon driver (prefer `codon_native_e6_bench.py`) |
| `run_inventory.sh` | Tiered `codon build` inventory → `test_runs/codon_inventory_*.log` |
| `bench_parse_kernel.sh` | Host CPython bench wrapper → `test_runs/codon_bench_*.log` |
| `run_codon_vs_314t_container.sh` | **Codon vs 3.14t** in pipeline image (Clang shim) |

## Tests

From git checkout (`HPCPerfStats/`):

```bash
/data/HPCPerfStats/.venv/bin/python3 -m pytest hpcperfstats/tests/test_codon_parse_kernel_parity.py -q
```

Optional inventory test (requires Codon on PATH):

```bash
HPCPERFSTATS_CODON=1 /data/HPCPerfStats/.venv/bin/python3 -m pytest hpcperfstats/tests/test_codon_inventory.py -q
```

## Benchmarks

```bash
chmod +x experiments/codon/run_inventory.sh experiments/codon/bench_parse_kernel.sh \
  experiments/codon/run_codon_vs_314t_container.sh
./experiments/codon/run_inventory.sh
./experiments/codon/bench_parse_kernel.sh
# Plan gate (Codon-native vs /opt/python3.14t) — requires Podman + hpcperfstats image:
./experiments/codon/run_codon_vs_314t_container.sh
```

Production FT baseline uses `/opt/python3.14t/bin/python` inside the **pipeline**
image (`python-image-interpreter-contract.mdc`).
