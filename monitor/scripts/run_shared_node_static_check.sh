#!/usr/bin/env bash
# Rebuild static bundle with --enable-shared-node-multi-jid and run make check.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
# Reuse PREFIX deps from a prior build_static_bundle when present.
export SKIP_DEPS="${SKIP_DEPS:-1}"
export SKIP_CLEAN="${SKIP_CLEAN:-0}"
./scripts/build_static_bundle.sh --enable-shared-node-multi-jid
make -C .build-static check
echo "run_shared_node_static_check: ok"
