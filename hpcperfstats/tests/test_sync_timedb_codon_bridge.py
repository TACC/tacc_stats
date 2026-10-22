"""Fail-closed Codon parse bridge (missing .so → CPython)."""

from __future__ import annotations

import sys
from types import ModuleType

import pytest

from hpcperfstats.dbload.lib import sync_timedb_codon_bridge as bridge


@pytest.fixture(autouse=True)
def _reset_bridge():
  bridge.reset_codon_bridge_for_tests()
  yield
  bridge.reset_codon_bridge_for_tests()


def test_missing_extension_returns_none(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv(bridge.CODON_FORCE_DISABLE_ENV, "1")
  assert bridge.try_codon_parse_collapse(["1.0 j h"]) is None
  assert bridge.try_codon_feed_collapse_fingerprint(["1.0 j h"]) is None
  assert bridge.codon_parse_available() is False


def test_loaded_extension_fingerprint_path(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  mod = ModuleType("fake_codon_parse")

  def _fp(lines: list[str]) -> tuple[int, int, float, float]:
    assert lines
    return (10, 5, 1.5, 2.0)

  mod.feed_and_collapse_fingerprint = _fp  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "fake_codon_parse", mod)
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_parse")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  bridge.reset_codon_bridge_for_tests()
  out = bridge.try_codon_feed_collapse_fingerprint(["x"])
  assert out == {
    "raw_stats": 10,
    "collapsed_rows": 5,
    "collapsed_value_sum": 1.5,
    "proc_rows": 2,
  }
  # Full parse API absent → None (CPython path)
  assert bridge.try_codon_parse_collapse(["x"]) is None


def test_loaded_extension_parse_stats_lines_codon_path(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  mod = ModuleType("fake_codon_parse_full")

  def _fp(lines: list[str]) -> tuple[int, int, float, float]:
    return (1, 1, 1.0, 0.0)

  def _parse(lines: list[str]) -> tuple[list[dict], list[dict]]:
    assert lines == ["row"]
    return ([{"type": "cpu", "event": "user", "value": 1.0}], [])

  mod.feed_and_collapse_fingerprint = _fp  # type: ignore[attr-defined]
  mod.parse_stats_lines_codon = _parse  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "fake_codon_parse_full", mod)
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_parse_full")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  bridge.reset_codon_bridge_for_tests()
  out = bridge.try_codon_parse_collapse(["row"])
  assert out is not None
  stats, procs = out
  assert stats[0]["event"] == "user"
  assert procs == []
  assert bridge.try_codon_feed_batch_parse(["row"]) == out


def test_parse_stats_lines_still_cpython_without_ext() -> None:
  from hpcperfstats.dbload.lib.sync_timedb_parsing import parse_stats_lines

  stats, procs = parse_stats_lines(
    [
      "!cpu user,W=64,U=1",
      "1000.0 J1 h1",
      "cpu 0 @full 1.0",
    ],
    0,
  )
  assert isinstance(stats, list)
  assert isinstance(procs, list)


def test_format_codon_parse_startup_line_disabled_by_env(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv(bridge.CODON_FORCE_DISABLE_ENV, "1")
  line = bridge.format_codon_parse_startup_line()
  assert line.startswith("codon_parse status=disabled")
  assert "HPCPERFSTATS_CODON_PARSE_DISABLE" in line
  assert bridge.codon_ingest_parse_enabled() is False


def test_format_codon_parse_startup_line_enabled_with_parse_api(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  mod = ModuleType("fake_codon_parse_startup")

  def _fp(lines: list[str]) -> tuple[int, int, float, float]:
    return (0, 0, 0.0, 0.0)

  def _parse(lines: list[str]) -> tuple[list, list]:
    return ([], [])

  mod.feed_and_collapse_fingerprint = _fp  # type: ignore[attr-defined]
  mod.parse_stats_lines_codon = _parse  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "fake_codon_parse_startup", mod)
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_parse_startup")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  bridge.reset_codon_bridge_for_tests()
  line = bridge.format_codon_parse_startup_line()
  assert line == (
    "codon_parse status=enabled module=fake_codon_parse_startup "
    "api=parse_stats_lines_codon"
  )
  assert bridge.codon_ingest_parse_enabled() is True
  logged: list[str] = []

  def _capture(msg: str, flush: bool = False) -> None:
    logged.append(msg)

  assert bridge.log_codon_parse_startup(printer=_capture) == line
  assert logged == [line]


def test_sync_timedb_main_logs_codon_parse_startup() -> None:
  """Startup path must call log_codon_parse_startup after ABI fingerprint."""
  from pathlib import Path

  src = (
    Path(__file__).resolve().parents[2]
    / "hpcperfstats"
    / "dbload"
    / "sync_timedb.py"
  ).read_text(encoding="utf-8")
  assert "log_codon_parse_startup" in src
  abi_idx = src.index("log_python_abi_startup()")
  codon_idx = src.index("log_codon_parse_startup()")
  assert abi_idx < codon_idx
