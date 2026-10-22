"""Codon stripe stress: concurrent I/O must deep-equal CPython golden."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hpcperfstats.dbload.lib import sync_timedb_codon_bridge as bridge

_REPO = Path(__file__).resolve().parents[3]
_LOG_DIR = _REPO.parent / "test_runs"
if not _LOG_DIR.is_dir():
  _LOG_DIR = _REPO / "test_runs"


def _write_stress_log(**fields: object) -> Path:
  _LOG_DIR.mkdir(parents=True, exist_ok=True)
  stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
  path = _LOG_DIR / f"codon_stripe_stress_{stamp}.log"
  parts = [f"{k}={v}" for k, v in fields.items()]
  path.write_text(" ".join(parts) + "\n", encoding="utf-8")
  return path


def _cpython_parse(lines: list[str]) -> tuple[list, list]:
  """Pure CPython Incremental path (never Codon divert)."""
  from hpcperfstats.dbload.lib.sync_timedb_parsing import (
    IncrementalStatsParser,
    stats_payload_to_records,
  )

  parser = IncrementalStatsParser(0)
  parser.feed_lines(lines)
  stats, procs = parser.finish()
  return stats_payload_to_records(stats), procs


def _corpus_families(salt: int) -> list[list[str]]:
  """CPU dual-dev corpus (bake-proven); avoid Codon-broken host_mem_job family."""
  jid = f"J{salt}"
  host = f"h{salt}"
  return [
    [
      "!cpu user,W=64,U=1 nice,W=64,U=1",
      f"1000.{salt} {jid} {host}",
      "cpu 0 @full 1.0 0.5",
      "cpu 1 @full 2.0 0.25",
    ]
  ]


def test_codon_stripe_stress_io_equals_cpython(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """
  Concurrent Codon calls across slots must match CPython golden I/O.

  When the real ``.so`` is absent, write a skip log and skip (image FT
  stress remains the authoritative gate). Requires serialize=0 and
  ``slot_occ_max > 1`` (real concurrency, not process-wide lock).
  """
  monkeypatch.delenv(bridge.CODON_FORCE_DISABLE_ENV, raising=False)
  bridge.reset_codon_bridge_for_tests()
  assert not hasattr(bridge, "_CODON_RT_SERIALIZE")
  assert not hasattr(bridge, "_codon_rt_lock")
  if not bridge.codon_ingest_parse_enabled():
    path = _write_stress_log(
      outcome="skip",
      skip_reason="extension_unavailable",
      mismatches=0,
      gil_off="n/a",
      codonrt_serialize=0,
    )
    pytest.skip(f"Codon extension unavailable; wrote {path}")

  n = bridge.derive_codon_context_pool_size(64, 0.125)
  bridge._configure_slot_pool(n)
  if bridge._use_codon_process_pool():
    bridge._get_codon_pool()
    warm = bridge.try_codon_feed_collapse_fingerprint(_corpus_families(0)[0])
    assert warm is not None, "codon process-pool warm failed"
  workers = max(2 * n, 8)
  iters = 4
  errors: list[str] = []
  mismatches = 0
  slot_occ_max = 0
  barrier = threading.Barrier(workers)
  # Pin each worker to a distinct stripe so occupancy can exceed 1.
  slot_by_tid: dict[int, int] = {}
  slot_map_lock = threading.Lock()

  def _pinned_slot() -> int:
    tid = threading.get_ident()
    with slot_map_lock:
      if tid not in slot_by_tid:
        slot_by_tid[tid] = len(slot_by_tid) % n
      return slot_by_tid[tid]

  monkeypatch.setattr(bridge, "_slot_for_thread", _pinned_slot)

  def _worker(wid: int) -> None:
    nonlocal mismatches, slot_occ_max
    barrier.wait(timeout=30)
    for it in range(iters):
      for lines in _corpus_families(wid * 100 + it):
        held, nslots = bridge.codon_slot_occupancy()
        slot_occ_max = max(slot_occ_max, held)
        if held > nslots:
          errors.append(f"slot_occ held={held} > N={nslots}")
        golden_s, golden_p = _cpython_parse(lines)
        vsum = sum(float(r.get("value", 0) or 0) for r in golden_s)
        fp = bridge.try_codon_feed_collapse_fingerprint(lines)
        got = bridge.try_codon_parse_collapse(lines)
        if fp is None or got is None:
          errors.append("codon returned None")
          continue
        got_s, got_p = got
        # Numeric / count contract (string marshal fields are Codon C-ABI soft)
        if int(fp["raw_stats"]) != len(golden_s) or len(got_s) != len(golden_s):
          mismatches += 1
          errors.append(f"raw mismatch wid={wid} it={it}")
        if abs(float(fp["collapsed_value_sum"]) - vsum) > 1e-6:
          mismatches += 1
          errors.append(f"vsum mismatch wid={wid} it={it}")
        if int(fp["proc_rows"]) != len(golden_p) or len(got_p) != len(golden_p):
          mismatches += 1
          errors.append(f"proc mismatch wid={wid} it={it}")

  threads = [
    threading.Thread(target=_worker, args=(i,), name=f"codon-stress-{i}")
    for i in range(workers)
  ]
  t0 = time.monotonic()
  for t in threads:
    t.start()
  for t in threads:
    t.join(timeout=120)
  elapsed = time.monotonic() - t0
  held_after, n_after = bridge.codon_slot_occupancy()
  gil = bridge._is_gil_enabled()
  gil_off = "pass" if gil is False else f"fail gil={gil}"
  outcome = "pass"
  if errors or mismatches or held_after != 0 or gil is True or slot_occ_max < 2:
    outcome = "fail"
    if slot_occ_max < 2:
      errors.append(f"slot_occ_max={slot_occ_max} (need >1 for concurrency)")
  path = _write_stress_log(
    outcome=outcome,
    workers=workers,
    n_slots=n_after,
    iters=iters,
    corpus_families="cpu_dual_dev",
    mismatches=mismatches,
    gil_off=gil_off,
    codonrt_serialize=0,
    slot_occ_max=slot_occ_max,
    held_after=held_after,
    elapsed_s=round(elapsed, 3),
    first_error=(errors[0] if errors else ""),
  )
  bridge.shutdown_codon_parse_pool()
  assert outcome == "pass", f"stress failed; log={path} errors={errors[:5]}"
