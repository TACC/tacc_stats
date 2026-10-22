"""Fail-closed Codon parse/collapse bridge for sync_timedb hot path.

Loads an optional Codon ``pyext`` module built against ``/opt/python3.14t``.
When the extension is missing, unloadable, flips the process GIL on, or returns
a fingerprint mismatch sentinel, callers keep the CPython
``IncrementalStatsParser`` path.

Native Codon entry uses a **spawn process pool** of size ``N`` (one codonrt
per worker) so concurrent callers never share one process-global codonrt.
``N = max(1, round(parse_pool * fraction))`` (fraction default ``0.125``).
Host unit tests / fake modules keep in-process per-slot locks. No process-wide
serialize lock in the parent.

Attributes:
  logger: Module logger for import/runtime Codon bridge diagnostics.
  CODON_EXT_ENV: Legacy env override for extension module import name (tests).
  CODON_FORCE_DISABLE_ENV: When set to a truthy value, always use CPython.
  CODON_PROCESS_POOL_ENV: When ``0``/false, force in-process Codon (N=1 on FT).
  CODON_PARSE_DIR: Baked pyext directory (``/opt/hpcperfstats/codon_parse``).
  MAX_CODON_SLOTS: Hard cap matching Codon kernel banks (32).
  DEFAULT_CONTEXT_POOL_FRACTION: Default stripe fraction (0.125).
  _codon_mod: Cached imported Codon extension module or ``False`` if unavailable.
  _codon_probe_done: Whether the import probe has run once.
  _codon_gil_ok: True when FT build kept GIL off after Codon import.
  _slot_n: Active stripe / Codon-worker count.
  _slot_locks: Per-slot ``threading.Lock`` list (in-process / test path).
  _slot_held: Current native Codon hold count (census).
  _slot_held_lock: Guards ``_slot_held``.
  _codon_workers: Popen Codon stdio servers for FT baked ``.so`` path.
  _codon_worker_cv: Condition guarding worker checkout / busy flags.
  _codon_atexit_registered: Whether ``atexit`` kill-only shutdown is registered.
"""

from __future__ import annotations

import atexit
import contextlib
import importlib
import logging
import os
import pickle
import struct
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

from hpcperfstats.dbload.lib.print_utils import log_print

logger = logging.getLogger(__name__)

CODON_EXT_ENV = "HPCPERFSTATS_CODON_PARSE_MODULE"
CODON_FORCE_DISABLE_ENV = "HPCPERFSTATS_CODON_PARSE_DISABLE"
CODON_PROCESS_POOL_ENV = "HPCPERFSTATS_CODON_PROCESS_POOL"
# Dockerfile codon-build install dir (supervisord PYTHONPATH; also self-wired).
CODON_PARSE_DIR = "/opt/hpcperfstats/codon_parse"
MAX_CODON_SLOTS = 32
DEFAULT_CONTEXT_POOL_FRACTION = 0.125

_codon_mod: Any | bool | None = None
_codon_probe_done: bool = False
_codon_gil_ok: bool = False
_slot_n: int = 1
_slot_locks: list[threading.Lock] = [threading.Lock()]
_slot_held: int = 0
_slot_held_lock = threading.Lock()
_codon_workers: list[dict[str, Any]] = []
_codon_worker_cv = threading.Condition()
_codon_atexit_registered: bool = False


def _truthy(raw: str | None) -> bool:
  """
  Return True when ``raw`` is a common truthy string.

  Args:
    raw (str | None): Environment value or None.

  Returns:
    bool: True for 1/true/yes/on (case-insensitive).

  Examples:
    >>> _truthy("yes")
    True
    >>> _truthy("0")
    False
  """
  if raw is None:
    return False
  return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_gil_enabled() -> bool | None:
  """
  Return process GIL enabled flag, or None when the probe is unavailable.

  Returns:
    bool | None: ``sys._is_gil_enabled()`` result, or None on older/missing API.

  Examples:
    >>> _is_gil_enabled() in (True, False, None)
    True
  """
  probe = getattr(sys, "_is_gil_enabled", None)
  if probe is None:
    return None
  try:
    return bool(probe())
  except Exception:
    return None


def _is_free_threaded_build() -> bool:
  """
  Return True when this interpreter was built with ``Py_GIL_DISABLED``.

  Host GIL ``.venv`` must not fail-closed Codon fakes; enforce GIL-off only
  on pipeline ``3.14t``.

  Returns:
    bool: True on free-threaded builds.

  Examples:
    >>> isinstance(_is_free_threaded_build(), bool)
    True
  """
  try:
    import sysconfig

    return bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
  except Exception:
    return False


def derive_codon_context_pool_size(
  parse_pool: int,
  fraction: float = DEFAULT_CONTEXT_POOL_FRACTION,
) -> int:
  """
  Derive striped Codon slot count from ingest parse width.

  Args:
    parse_pool (int): ``sync_ingest_pool_processes`` (or test override).
    fraction (float): ``sync_codon_context_pool_fraction`` (default 0.125).

  Returns:
    int: ``N`` in ``[1, MAX_CODON_SLOTS]``.

  Examples:
    >>> derive_codon_context_pool_size(64, 0.125)
    8
    >>> derive_codon_context_pool_size(1, 0.125)
    1
  """
  pool = max(1, int(parse_pool))
  frac = float(fraction)
  if frac <= 0.0:
    return 1
  return min(MAX_CODON_SLOTS, max(1, round(pool * frac)))


def _configure_slot_pool(n: int) -> None:
  """
  Install ``n`` per-slot locks / Codon-worker width for the process.

  Recreates the spawn executor when width changes so ``max_workers`` matches.

  Args:
    n (int): Slot count (>= 1).

  Returns:
    None

  Examples:
    >>> _configure_slot_pool(1)
  """
  global _slot_n, _slot_locks
  n = max(1, min(MAX_CODON_SLOTS, int(n)))
  prev = _slot_n
  _slot_n = n
  _slot_locks = [threading.Lock() for _ in range(n)]
  if prev != n:
    _shutdown_codon_pool()


def configure_codon_context_pool_from_ini() -> int:
  """
  Configure stripe / Codon-worker width from conf_parser (parse pool * fraction).

  Returns:
    int: Configured slot / worker count ``N``.

  Examples:
    >>> configure_codon_context_pool_from_ini() >= 1  # doctest: +SKIP
    True
  """
  try:
    from hpcperfstats.dbload.lib import conf_parser as cfg

    pool = int(cfg.get_sync_ingest_pool_processes())
    frac = float(cfg.get_sync_codon_context_pool_fraction())
  except Exception:
    pool = 64
    frac = DEFAULT_CONTEXT_POOL_FRACTION
  n = derive_codon_context_pool_size(pool, frac)
  _configure_slot_pool(n)
  # Warm Popen Codon workers on the configuring thread (not after a
  # multi-thread barrier). When process-pool is off, force N=1 so
  # in-process codonrt is never entered from two threads (SIGSEGV).
  if _use_codon_process_pool() and _load_codon_module() is not None:
    _get_codon_pool()
  elif (
    _is_free_threaded_build()
    and _load_codon_module() is not None
    and not _use_codon_process_pool()
  ):
    # FT + process-pool opted out: single in-process slot (codonrt safety).
    _configure_slot_pool(1)
    return 1
  return n


def codon_context_pool_size() -> int:
  """
  Return the configured Codon stripe slot count.

  Returns:
    int: Current ``N``.

  Examples:
    >>> codon_context_pool_size() >= 1
    True
  """
  return max(1, int(_slot_n))


def codon_slot_occupancy() -> tuple[int, int]:
  """
  Return ``(held, N)`` for census ``codon_slot_occ=held/N``.

  Returns:
    tuple[int, int]: Slots currently under lock and configured ``N``.

  Examples:
    >>> held, n = codon_slot_occupancy()
    >>> held >= 0 and n >= 1
    True
  """
  with _slot_held_lock:
    return int(_slot_held), codon_context_pool_size()


def format_codon_slot_occ_census_token() -> str:
  """
  Return greppable `` codon_slot_occ=held/N`` (leading space) or empty.

  Returns:
    str: Census token when Codon is enabled; else empty string.

  Examples:
    >>> isinstance(format_codon_slot_occ_census_token(), str)
    True
  """
  if not codon_ingest_parse_enabled():
    return ""
  held, n = codon_slot_occupancy()
  return f" codon_slot_occ={held}/{n}"


def _slot_for_thread() -> int:
  """
  Bind the calling thread to a stripe slot.

  Returns:
    int: Slot index in ``[0, N)``.

  Examples:
    >>> 0 <= _slot_for_thread() < codon_context_pool_size()
    True
  """
  n = codon_context_pool_size()
  return hash(threading.get_ident()) % n


def _call_with_slot_lock(fn: Callable[..., Any]) -> Any:
  """
  Run ``fn(slot=…)`` under the stripe lock for this thread; update occupancy.

  Args:
    fn (Callable[..., Any]): Callable accepting keyword ``slot``.

  Returns:
    Any: ``fn`` return value.

  Examples:
    >>> _call_with_slot_lock(lambda slot: slot) in range(MAX_CODON_SLOTS)
    True
  """
  global _slot_held
  slot = _slot_for_thread()
  lock = _slot_locks[slot]
  lock.acquire()
  with _slot_held_lock:
    _slot_held += 1
  try:
    return fn(slot=slot)
  finally:
    with _slot_held_lock:
      _slot_held = max(0, _slot_held - 1)
    lock.release()


def _use_codon_process_pool() -> bool:
  """
  Return True when FT baked ``.so`` should run in spawn workers.

  Host unit fakes set ``CODON_EXT_ENV`` and must stay in-process.

  Returns:
    bool: True for pipeline FT + baked pyext without env module override.

  Examples:
    >>> isinstance(_use_codon_process_pool(), bool)
    True
  """
  if not _is_free_threaded_build():
    return False
  if os.environ.get(CODON_EXT_ENV):
    return False
  # Opt out for FT soak / debug when Popen workers wedge pytest teardown.
  raw = os.environ.get(CODON_PROCESS_POOL_ENV)
  if raw is not None and raw.strip().lower() in {"0", "false", "no", "off"}:
    return False
  so_path = os.path.join(CODON_PARSE_DIR, "hpcperfstats_codon_parse.so")
  return os.path.isfile(so_path)


def _spawn_codon_worker() -> dict[str, Any]:
  """
  Start one Codon stdio server process (``codon_process_worker``).

  Returns:
    dict[str, Any]: ``{proc, lock, busy}`` worker record.

  Examples:
    >>> sorted(_spawn_codon_worker.__annotations__)
    ['return']
  """
  env = os.environ.copy()
  env.setdefault("OMP_NUM_THREADS", "1")
  env["PYTHONPATH"] = f"{CODON_PARSE_DIR}:{env.get('PYTHONPATH', '')}".rstrip(
    ":"
  )
  proc = subprocess.Popen(
    [sys.executable, "-m", "hpcperfstats.dbload.lib.codon_process_worker"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    env=env,
    bufsize=0,
  )
  return {"proc": proc, "lock": threading.Lock(), "busy": False}


def _get_codon_pool() -> list[dict[str, Any]]:
  """
  Lazily start ``N`` Codon Popen stdio servers.

  Returns:
    list[dict[str, Any]]: Worker records.

  Examples:
    >>> isinstance(_get_codon_pool, Callable)
    True
  """
  global _codon_workers, _codon_atexit_registered
  with _codon_worker_cv:
    if not _codon_workers:
      n = codon_context_pool_size()
      _codon_workers = [_spawn_codon_worker() for _ in range(n)]
      if not _codon_atexit_registered:
        atexit.register(_shutdown_codon_pool)
        _codon_atexit_registered = True
    return _codon_workers


def _popen_rpc(kind: str, lines: list[str]) -> Any:
  """
  Send ``(kind, lines)`` to a free Codon Popen worker; return result.

  Occupancy (``_slot_held``) increments only while a worker is checked out,
  so ``held`` never exceeds ``N``.

  Args:
    kind (str): ``fp`` or ``parse``.
    lines (list[str]): Stats lines.

  Returns:
    Any: Worker return payload.

  Raises:
    RuntimeError: When the worker returns an error envelope.

  Examples:
    >>> callable(_popen_rpc)
    True
  """
  global _slot_held
  workers = _get_codon_pool()
  worker: dict[str, Any] | None = None
  with _codon_worker_cv:
    while worker is None:
      for cand in workers:
        if not cand["busy"]:
          cand["busy"] = True
          worker = cand
          break
      if worker is None:
        _codon_worker_cv.wait(timeout=1.0)
        workers = _codon_workers or workers
  if worker is None:
    raise RuntimeError("codon worker checkout failed")
  with _slot_held_lock:
    _slot_held += 1
  try:
    with worker["lock"]:
      proc = worker["proc"]
      if proc.poll() is not None:
        worker["proc"] = _spawn_codon_worker()["proc"]
        proc = worker["proc"]
      payload = pickle.dumps(
        (kind, list(lines)), protocol=pickle.HIGHEST_PROTOCOL
      )
      if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("codon worker pipes missing")
      proc.stdin.write(struct.pack("!I", len(payload)))
      proc.stdin.write(payload)
      proc.stdin.flush()
      raw_len = proc.stdout.read(4)
      if not raw_len or len(raw_len) < 4:
        raise RuntimeError("codon worker EOF")
      (n,) = struct.unpack("!I", raw_len)
      blob = proc.stdout.read(n)
      status, body = pickle.loads(blob)  # noqa: S301 — trusted child
      if status != "ok":
        raise RuntimeError(str(body))
      return body
  finally:
    with _slot_held_lock:
      _slot_held = max(0, _slot_held - 1)
    with _codon_worker_cv:
      worker["busy"] = False
      _codon_worker_cv.notify()


def _call_via_codon_process_pool(
  kind: str,
  lines: list[str],
) -> Any:
  """
  Run Codon ``kind`` on the Popen worker pool; update occupancy.

  Args:
    kind (str): ``fp`` or ``parse``.
    lines (list[str]): Stats lines.

  Returns:
    Any: Worker return value.

  Examples:
    >>> isinstance(_call_via_codon_process_pool, Callable)
    True
  """
  return _popen_rpc(kind, lines)


def _shutdown_codon_pool() -> None:
  """
  SIGKILL Codon Popen workers (FT-safe; no multiprocessing teardown).

  Returns:
    None

  Examples:
    >>> _shutdown_codon_pool()
  """
  global _codon_workers
  with _codon_worker_cv:
    workers = list(_codon_workers)
    _codon_workers = []
    _codon_worker_cv.notify_all()
  for worker in workers:
    proc = worker.get("proc")
    if proc is None:
      continue
    with contextlib.suppress(Exception):
      if proc.stdin is not None:
        proc.stdin.close()
    with contextlib.suppress(Exception):
      proc.kill()
    # Do not wait/poll — under FT, Popen.wait can spin the caller thread.


def shutdown_codon_parse_pool() -> None:
  """
  Public teardown for Codon spawn workers (supervisor exit / soak finally).

  Returns:
    None

  Examples:
    >>> shutdown_codon_parse_pool()
  """
  _shutdown_codon_pool()


def reset_codon_bridge_for_tests() -> None:
  """
  Clear the cached Codon extension probe (unit tests only).

  Returns:
    None

  Examples:
    >>> reset_codon_bridge_for_tests()
  """
  global _codon_mod, _codon_probe_done, _codon_gil_ok, _slot_held
  _shutdown_codon_pool()
  _codon_mod = None
  _codon_probe_done = False
  _codon_gil_ok = False
  _slot_held = 0
  _configure_slot_pool(1)


def codon_parse_available() -> bool:
  """
  Return whether a Codon parse extension is importable and enabled.

  Returns:
    bool: True when the extension module loaded successfully.

  Examples:
    >>> isinstance(codon_parse_available(), bool)
    True
  """
  return _load_codon_module() is not None


def codon_ingest_parse_enabled() -> bool:
  """
  Return whether Codon will divert ``parse_stats_lines`` (full parse API).

  Fingerprint-only modules count as unavailable for ingest divert.

  Returns:
    bool: True when ``parse_stats_lines_codon`` is present on the loaded ext.

  Examples:
    >>> isinstance(codon_ingest_parse_enabled(), bool)
    True
  """
  mod = _load_codon_module()
  return mod is not None and callable(
    getattr(mod, "parse_stats_lines_codon", None)
  )


def format_codon_parse_startup_line() -> str:
  """
  Build a greppable Codon ingest-parse status line for daemon startup.

  Returns:
    str: ``codon_parse status=enabled|disabled …`` for operator logs.

  Examples:
    >>> line = format_codon_parse_startup_line()
    >>> line.startswith("codon_parse status=")
    True
  """
  if _truthy(os.environ.get(CODON_FORCE_DISABLE_ENV)):
    return "codon_parse status=disabled reason=HPCPERFSTATS_CODON_PARSE_DISABLE"
  mod = _load_codon_module()
  if mod is None:
    gil = _is_gil_enabled()
    if gil is True and _codon_probe_done and not _codon_gil_ok:
      return "codon_parse status=disabled reason=gil_enabled_after_import"
    return "codon_parse status=disabled reason=extension_unavailable"
  mod_name = getattr(mod, "__name__", "unknown")
  if not callable(getattr(mod, "parse_stats_lines_codon", None)):
    return (
      "codon_parse status=disabled "
      f"reason=missing_parse_stats_lines_codon module={mod_name}"
    )
  n = codon_context_pool_size()
  gil_tok = "gil=off" if _codon_gil_ok else "gil=unknown"
  return (
    f"codon_parse status=enabled module={mod_name} "
    f"api=parse_stats_lines_codon {gil_tok} contexts={n} "
    f"codon_mode={'process_pool' if _use_codon_process_pool() else 'in_process'} "
    "codonrt_serialize=0"
  )


def log_codon_parse_startup(
  *,
  printer: Callable[..., Any] | None = None,
) -> str:
  """
  Log Codon ingest-parse status once via ``log_print`` (or a test double).

  Configures the stripe pool from INI before formatting the status line.

  Args:
    printer (Callable[..., Any] | None): Optional print-like callable with
      ``flush`` support. Defaults to ``log_print``.

  Returns:
    str: The line that was logged.

  Examples:
    >>> logged: list[str] = []
    >>> def _capture(msg: str, flush: bool = False) -> None:
    ...   logged.append(msg)
    >>> out = log_codon_parse_startup(printer=_capture)
    >>> out.startswith("codon_parse status=")
    True
    >>> logged == [out]
    True
  """
  configure_codon_context_pool_from_ini()
  line = format_codon_parse_startup_line()
  emit = log_print if printer is None else printer
  emit(line, flush=True)
  return line


def _ensure_codon_parse_dir_on_sys_path() -> None:
  """
  Put the baked Codon pyext directory on ``sys.path`` when present.

  Supervisord sets ``PYTHONPATH=/opt/hpcperfstats/codon_parse``, but compose
  pytest fallbacks often overwrite ``PYTHONPATH`` with the repo root only.
  Self-wiring keeps Arm-B / pipeline imports fail-closed to the real ``.so``.

  Returns:
    None

  Examples:
    >>> isinstance(CODON_PARSE_DIR, str)
    True
  """
  if os.path.isdir(CODON_PARSE_DIR) and CODON_PARSE_DIR not in sys.path:
    sys.path.insert(0, CODON_PARSE_DIR)


def _load_codon_module() -> Any | None:
  """
  Import and cache the Codon pyext module, or return None (fail closed).

  After a successful import, fail closed if ``sys._is_gil_enabled()`` is True
  (``Py_MOD_GIL_USED`` or accidental GIL re-enable).

  Returns:
    Any | None: Loaded module, or None when disabled/missing/broken.

  Examples:
    >>> _load_codon_module() is None or hasattr(
    ...   _load_codon_module(), "__name__"
    ... )
    True
  """
  global _codon_mod, _codon_probe_done, _codon_gil_ok
  if _truthy(os.environ.get(CODON_FORCE_DISABLE_ENV)):
    return None
  if _codon_probe_done:
    return None if _codon_mod is False else _codon_mod
  _codon_probe_done = True
  mod_name = (
    os.environ.get(CODON_EXT_ENV) or "hpcperfstats_codon_parse"
  ).strip()
  if not mod_name:
    _codon_mod = False
    return None
  _ensure_codon_parse_dir_on_sys_path()
  # Avoid nested OpenMP under multi-slot Codon entry (bundled libomp).
  os.environ.setdefault("OMP_NUM_THREADS", "1")
  try:
    mod = importlib.import_module(mod_name)
  except Exception as exc:
    logger.debug("codon parse extension unavailable: %s", exc)
    _codon_mod = False
    return None
  if not hasattr(mod, "feed_and_collapse_fingerprint"):
    logger.warning(
      "codon parse module %s missing feed_and_collapse_fingerprint; "
      "using CPython",
      mod_name,
    )
    _codon_mod = False
    return None
  if _is_free_threaded_build():
    gil = _is_gil_enabled()
    if gil is True:
      logger.warning(
        "codon parse module %s re-enabled process GIL; fail-closed to CPython",
        mod_name,
      )
      _codon_mod = False
      _codon_gil_ok = False
      return None
    _codon_gil_ok = gil is False
  else:
    # Host GIL ABI / unit fakes: do not require gil=off.
    _codon_gil_ok = True
  _codon_mod = mod
  return mod


def _invoke_mod_fn(mod: Any, name: str, lines: list[str], slot: int) -> Any:
  """
  Call ``mod.name(lines, slot)`` with one-arg fallback for test doubles.

  Args:
    mod (Any): Loaded extension or fake module.
    name (str): Attribute name of the callable.
    lines (list[str]): Stats lines.
    slot (int): Stripe slot index.

  Returns:
    Any: Callable return value.

  Examples:
    >>> class _M:
    ...   @staticmethod
    ...   def feed_and_collapse_fingerprint(lines, slot=0):
    ...     return (0, 0, 0.0, 0.0)
    >>> _invoke_mod_fn(_M(), "feed_and_collapse_fingerprint", [], 0)
    (0, 0, 0.0, 0.0)
  """
  fn = getattr(mod, name)
  try:
    return fn(list(lines), slot)
  except TypeError:
    return fn(list(lines))


def try_codon_feed_collapse_fingerprint(
  lines: list[str],
) -> dict[str, Any] | None:
  """
  Run Codon feed+collapse fingerprint on ``lines``, or None to use CPython.

  Args:
    lines (list[str]): Stats file text lines (same contract as feed_lines).

  Returns:
    dict[str, Any] | None: Fingerprint keys ``raw_stats``, ``collapsed_rows``,
    ``collapsed_value_sum``, ``proc_rows`` when Codon ran; otherwise None.

  Examples:
    >>> try_codon_feed_collapse_fingerprint([]) is None or isinstance(
    ...   try_codon_feed_collapse_fingerprint([]), dict
    ... )
    True
  """
  mod = _load_codon_module()
  if mod is None:
    return None

  try:
    if _use_codon_process_pool():
      raw_stats, collapsed_rows, value_sum, proc_rows = (
        _call_via_codon_process_pool("fp", lines)
      )
    else:
      raw_stats, collapsed_rows, value_sum, proc_rows = _call_with_slot_lock(
        lambda *, slot: _invoke_mod_fn(
          mod, "feed_and_collapse_fingerprint", lines, slot
        )
      )
  except Exception as exc:
    logger.warning("codon feed_and_collapse failed; using CPython: %s", exc)
    return None
  return {
    "raw_stats": int(raw_stats),
    "collapsed_rows": int(collapsed_rows),
    "collapsed_value_sum": float(value_sum),
    "proc_rows": int(proc_rows),
  }


def try_codon_parse_collapse(lines: list[str]) -> tuple[Any, Any] | None:
  """
  Prefer Codon feed+collapse when the extension exposes full parse output.

  When only the fingerprint API is present (microbench extension), return
  None so callers keep CPython ``IncrementalStatsParser`` for ORM ingest.

  Args:
    lines (list[str]): Stats file text lines.

  Returns:
    tuple[Any, Any] | None: ``(stats_records, proc_rows)`` or None.

  Examples:
    >>> try_codon_parse_collapse([]) is None or isinstance(
    ...   try_codon_parse_collapse([]), tuple
    ... )
    True
  """
  mod = _load_codon_module()
  if mod is None:
    return None
  if getattr(mod, "parse_stats_lines_codon", None) is None:
    return None

  try:
    if _use_codon_process_pool():
      return _call_via_codon_process_pool("parse", lines)
    return _call_with_slot_lock(
      lambda *, slot: _invoke_mod_fn(
        mod, "parse_stats_lines_codon", lines, slot
      )
    )
  except Exception as exc:
    logger.warning(
      "codon parse_stats_lines_codon failed; using CPython: %s", exc
    )
    return None


def try_codon_feed_batch_parse(
  lines: list[str],
) -> tuple[Any, Any] | None:
  """
  Parse one streaming flush window via ``parse_stats_lines_codon``.

  Schema must be included in ``lines`` (or prior lines in the same call).
  Fail-closed to None when the extension lacks the full parse export.

  Args:
    lines (list[str]): Stats lines for one take/finish boundary.

  Returns:
    tuple[Any, Any] | None: ``(stats_records, proc_rows)`` or None.

  Examples:
    >>> try_codon_feed_batch_parse([]) is None or isinstance(
    ...   try_codon_feed_batch_parse([]), tuple
    ... )
    True
  """
  return try_codon_parse_collapse(lines)
