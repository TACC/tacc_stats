"""Fail-closed Codon parse/collapse bridge for sync_timedb hot path.

Loads an optional Codon ``pyext`` module built against ``/opt/python3.14t``.
When the extension is missing, unloadable, or returns a fingerprint mismatch
sentinel, callers keep the CPython ``IncrementalStatsParser`` path.

Attributes:
  logger: Module logger for import/runtime Codon bridge diagnostics.
  CODON_EXT_ENV: Legacy env override for extension module import name (tests).
  CODON_FORCE_DISABLE_ENV: When set to a truthy value, always use CPython.
  _codon_mod: Cached imported Codon extension module or ``False`` if unavailable.
  _codon_probe_done: Whether the import probe has run once.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Callable
from typing import Any

from hpcperfstats.dbload.lib.print_utils import log_print

logger = logging.getLogger(__name__)

CODON_EXT_ENV = "HPCPERFSTATS_CODON_PARSE_MODULE"
CODON_FORCE_DISABLE_ENV = "HPCPERFSTATS_CODON_PARSE_DISABLE"

_codon_mod: Any | bool | None = None
_codon_probe_done: bool = False


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


def reset_codon_bridge_for_tests() -> None:
  """
  Clear the cached Codon extension probe (unit tests only).

  Returns:
    None

  Examples:
    >>> reset_codon_bridge_for_tests()
  """
  global _codon_mod, _codon_probe_done
  _codon_mod = None
  _codon_probe_done = False


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
    return "codon_parse status=disabled reason=extension_unavailable"
  mod_name = getattr(mod, "__name__", "unknown")
  if not callable(getattr(mod, "parse_stats_lines_codon", None)):
    return (
      "codon_parse status=disabled "
      f"reason=missing_parse_stats_lines_codon module={mod_name}"
    )
  return (
    f"codon_parse status=enabled module={mod_name} api=parse_stats_lines_codon"
  )


def log_codon_parse_startup(
  *,
  printer: Callable[..., Any] | None = None,
) -> str:
  """
  Log Codon ingest-parse status once via ``log_print`` (or a test double).

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
  line = format_codon_parse_startup_line()
  emit = log_print if printer is None else printer
  emit(line, flush=True)
  return line


def _load_codon_module() -> Any | None:
  """
  Import and cache the Codon pyext module, or return None (fail closed).

  Returns:
    Any | None: Loaded module, or None when disabled/missing/broken.

  Examples:
    >>> _load_codon_module() is None or hasattr(
    ...   _load_codon_module(), "__name__"
    ... )
    True
  """
  global _codon_mod, _codon_probe_done
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
  _codon_mod = mod
  return mod


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
    raw_stats, collapsed_rows, value_sum, proc_rows = (
      mod.feed_and_collapse_fingerprint(list(lines))
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
  parse_fn = getattr(mod, "parse_stats_lines_codon", None)
  if parse_fn is None:
    return None
  try:
    return parse_fn(list(lines))
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
