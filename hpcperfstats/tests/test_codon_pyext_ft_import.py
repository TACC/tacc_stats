"""Optional FT pyext smoke — skip unless HPCPERFSTATS_CODON_PYEXT_DIR is set."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from hpcperfstats.dbload.lib import sync_timedb_codon_bridge as bridge

_PYEXT_DIR = os.environ.get("HPCPERFSTATS_CODON_PYEXT_DIR", "").strip()


@pytest.fixture(autouse=True)
def _reset_bridge():
  bridge.reset_codon_bridge_for_tests()
  yield
  bridge.reset_codon_bridge_for_tests()


def _ft_artifacts_ready() -> bool:
  if not _PYEXT_DIR:
    return False
  root = Path(_PYEXT_DIR)
  return (root / "hpcperfstats_codon_parse.so").is_file() and (
    root / "libhpcperfstats_codon_kernel.so"
  ).is_file()


@pytest.mark.skipif(
  not _ft_artifacts_ready(),
  reason="HPCPERFSTATS_CODON_PYEXT_DIR with both .so artifacts required",
)
def test_bridge_ft_pyext_fingerprint_empty(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """Bridge loads FT-built module and returns empty fingerprint zeros."""
  gil_fn = getattr(sys, "_is_gil_enabled", None)
  if gil_fn is not None and gil_fn():
    pytest.skip("requires free-threaded interpreter (3.14t)")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  monkeypatch.delenv(bridge.CODON_EXT_ENV, raising=False)
  monkeypatch.syspath_prepend(_PYEXT_DIR)
  bridge.reset_codon_bridge_for_tests()
  sys.path.insert(0, _PYEXT_DIR)
  out = bridge.try_codon_feed_collapse_fingerprint([])
  assert out == {
    "raw_stats": 0,
    "collapsed_rows": 0,
    "collapsed_value_sum": 0.0,
    "proc_rows": 0.0,
  }
  assert bridge.codon_parse_available() is True
