"""Class-free Codon feed_collapse contract + fingerprint parity."""

from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path

import pandas as pd

FEED_COLLAPSE = (
  Path(__file__).resolve().parents[2]
  / "hpcperfstats"
  / "dbload"
  / "codon"
  / "feed_collapse.py"
)


def _load_feed_collapse():
  spec = importlib.util.spec_from_file_location(
    "feed_collapse_under_test", FEED_COLLAPSE
  )
  assert spec is not None and spec.loader is not None
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod


def test_feed_collapse_source_has_no_class_defs() -> None:
  """Codon pyext rejects custom classes; compile unit must stay class-free."""
  tree = ast.parse(FEED_COLLAPSE.read_text(encoding="utf-8"))
  classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
  assert classes == [], f"unexpected class defs: {classes}"


def test_feed_and_collapse_fingerprint_matches_incremental_e6() -> None:
  """Fingerprint from class-free unit matches CPython Incremental plain sum."""
  from hpcperfstats.dbload.lib.sync_timedb_parsing import (
    _COLLAPSE_GROUP_COLS,
    IncrementalStatsParser,
    stats_payload_to_records,
  )

  mod = _load_feed_collapse()
  lines = mod.build_e6_payload_lines(40)
  raw_b, collapsed_b, sum_b, proc_b = mod.feed_and_collapse_fingerprint(lines)

  p = IncrementalStatsParser(0)
  p.feed_lines(list(lines))
  stats, procs = p.finish()
  stats = stats_payload_to_records(stats)
  df = pd.DataFrame(stats)
  df = df[~df["type"].isin({"nvidia_gpu", "amd_gpu", "intel_gpu"})]
  collapsed = (
    df.groupby(_COLLAPSE_GROUP_COLS, dropna=False, observed=True)["value"]
    .sum(min_count=1)
    .reset_index()
  )
  raw_a = len(stats)
  collapsed_a = len(collapsed)
  sum_a = float(collapsed["value"].sum()) if collapsed_a else 0.0
  proc_a = float(len(procs))

  assert raw_b == raw_a
  assert collapsed_b == collapsed_a
  assert math.isclose(sum_b, sum_a, rel_tol=1e-9, abs_tol=1e-6)
  assert proc_b == proc_a


def test_empty_lines_fingerprint_zeros() -> None:
  mod = _load_feed_collapse()
  assert mod.feed_and_collapse_fingerprint([]) == (0, 0, 0.0, 0.0)
