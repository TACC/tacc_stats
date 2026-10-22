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


def test_ensure_codon_parse_dir_on_sys_path_idempotent(
  tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
  """Bake dir is prepended once when present (pytest PYTHONPATH overwrite)."""
  d = tmp_path / "codon_parse"
  d.mkdir()
  monkeypatch.setattr(bridge, "CODON_PARSE_DIR", str(d))
  while str(d) in sys.path:
    sys.path.remove(str(d))
  bridge._ensure_codon_parse_dir_on_sys_path()
  assert sys.path[0] == str(d)
  bridge._ensure_codon_parse_dir_on_sys_path()
  assert sys.path.count(str(d)) == 1


def test_benchmark_inner_keeps_codon_parse_on_pythonpath() -> None:
  """loaded48 inner must not drop /opt/hpcperfstats/codon_parse from PYTHONPATH."""
  from pathlib import Path

  text = Path("tests/run_sync_timedb_benchmark_inner.sh").read_text(
    encoding="utf-8"
  )
  assert "/opt/hpcperfstats/codon_parse" in text
  assert 'PYTHONPATH="/opt/hpcperfstats/codon_parse:' in text


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
  bridge._configure_slot_pool(8)
  line = bridge.format_codon_parse_startup_line()
  assert line == (
    "codon_parse status=enabled module=fake_codon_parse_startup "
    "api=parse_stats_lines_codon gil=off contexts=8 "
    "codon_mode=in_process codonrt_serialize=0"
  )
  assert bridge.codon_ingest_parse_enabled() is True
  logged: list[str] = []

  def _capture(msg: str, flush: bool = False) -> None:
    logged.append(msg)

  assert bridge.log_codon_parse_startup(printer=_capture) == line
  assert logged == [line]


def test_sync_timedb_main_logs_codon_parse_startup() -> None:
  """CLI main and in-process supervisor both size Codon; CLI after ABI log."""
  from pathlib import Path

  src = (
    Path(__file__).resolve().parents[2]
    / "hpcperfstats"
    / "dbload"
    / "sync_timedb.py"
  ).read_text(encoding="utf-8")
  assert src.count("log_codon_parse_startup()") >= 2
  abi_idx = src.index("log_python_abi_startup()")
  # CLI path: first codon call after ABI fingerprint.
  codon_after_abi = src.index("log_codon_parse_startup()", abi_idx)
  assert codon_after_abi > abi_idx
  sup_at = src.index("def run_sync_timedb_supervisor_from_parsed(")
  assert "log_codon_parse_startup()" in src[sup_at:abi_idx]


def test_derive_codon_context_pool_size_fraction() -> None:
  assert bridge.derive_codon_context_pool_size(64, 0.125) == 8
  assert bridge.derive_codon_context_pool_size(1, 0.125) == 1
  assert bridge.derive_codon_context_pool_size(96, 0.125) == 12


def test_codonrt_serialize_default_off() -> None:
  """Process-wide codonrt serialize is removed; stripes only."""
  assert not hasattr(bridge, "_CODON_RT_SERIALIZE")
  assert not hasattr(bridge, "_codon_rt_lock")
  line = bridge.format_codon_parse_startup_line()
  # Fake/unavailable may disable; when enabled must show serialize=0.
  if "status=enabled" in line:
    assert "codonrt_serialize=0" in line
    assert "codon_mode=" in line


def test_use_codon_process_pool_false_with_ext_env(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """Host fakes must stay in-process (CODON_EXT_ENV set)."""
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_mod")
  monkeypatch.setattr(bridge, "_is_free_threaded_build", lambda: True)
  monkeypatch.setattr(bridge.os.path, "isfile", lambda _p: True)
  assert bridge._use_codon_process_pool() is False


def test_gil_enabled_after_import_fail_closed(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  mod = ModuleType("fake_codon_gil_on")

  def _fp(lines: list[str]) -> tuple[int, int, float, float]:
    return (0, 0, 0.0, 0.0)

  mod.feed_and_collapse_fingerprint = _fp  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "fake_codon_gil_on", mod)
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_gil_on")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  monkeypatch.setattr(bridge, "_is_free_threaded_build", lambda: True)
  monkeypatch.setattr(bridge, "_is_gil_enabled", lambda: True)
  bridge.reset_codon_bridge_for_tests()
  assert bridge.codon_parse_available() is False
  line = bridge.format_codon_parse_startup_line()
  assert "gil_enabled_after_import" in line or "extension_unavailable" in line


def test_slot_lock_held_only_during_native_call(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  mod = ModuleType("fake_codon_slot")
  held_during: list[int] = []

  def _parse(lines: list[str], slot: int = 0) -> tuple[list, list]:
    held, n = bridge.codon_slot_occupancy()
    held_during.append(held)
    assert n >= 1
    assert held >= 1
    return ([], [])

  def _fp(lines: list[str], slot: int = 0) -> tuple[int, int, float, float]:
    return (0, 0, 0.0, 0.0)

  mod.feed_and_collapse_fingerprint = _fp  # type: ignore[attr-defined]
  mod.parse_stats_lines_codon = _parse  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "fake_codon_slot", mod)
  monkeypatch.setenv(bridge.CODON_EXT_ENV, "fake_codon_slot")
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  bridge.reset_codon_bridge_for_tests()
  bridge._configure_slot_pool(4)
  assert bridge.try_codon_parse_collapse(["x"]) == ([], [])
  assert held_during and held_during[0] >= 1
  held, n = bridge.codon_slot_occupancy()
  assert held == 0
  assert n == 4
  assert "codon_slot_occ=0/4" in bridge.format_codon_slot_occ_census_token()


def test_pyext_source_declares_gil_not_used() -> None:
  from pathlib import Path

  src = (
    Path(__file__).resolve().parents[2]
    / "hpcperfstats"
    / "dbload"
    / "codon"
    / "pyext_ft_init.c"
  ).read_text(encoding="utf-8")
  assert "Py_MOD_GIL_NOT_USED" in src
  assert "Py_MOD_GIL_USED" not in src


def test_bake_script_requires_gil_off_smoke() -> None:
  from pathlib import Path

  text = (
    Path(__file__).resolve().parents[2]
    / "hpcperfstats"
    / "dbload"
    / "codon"
    / "build_codon_ext.sh"
  ).read_text(encoding="utf-8")
  assert "codon_pyext_314t_gil_off=pass" in text
  assert "Py_MOD_GIL_NOT_USED" in text or "GIL_NOT_USED" in (
    Path(__file__).resolve().parents[2]
    / "hpcperfstats"
    / "dbload"
    / "codon"
    / "pyext_ft_init.c"
  ).read_text(encoding="utf-8")
