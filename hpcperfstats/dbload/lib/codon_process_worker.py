"""Minimal spawn-worker / Popen server for Codon parse (no Django imports).

Used both as:
- picklable callables for unit tests (rare), and
- ``python -m hpcperfstats.dbload.lib.codon_process_worker`` stdio servers
  (one codonrt per OS process; parent SIGKILLs on shutdown).

Attributes:
  CODON_PARSE_DIR: Baked pyext directory (``/opt/hpcperfstats/codon_parse``).
"""

from __future__ import annotations

import importlib
import os
import pickle
import struct
import sys
from typing import Any

CODON_PARSE_DIR = "/opt/hpcperfstats/codon_parse"


def _ensure_codon_on_path() -> None:
  """
  Insert baked pyext dir on ``sys.path`` when present.

  Returns:
    None: Always ``None``.

  Examples:
    >>> _ensure_codon_on_path() is None
    True
  """
  os.environ.setdefault("OMP_NUM_THREADS", "1")
  if CODON_PARSE_DIR not in sys.path and os.path.isdir(CODON_PARSE_DIR):
    sys.path.insert(0, CODON_PARSE_DIR)


def codon_worker_fingerprint(lines: list[str]) -> tuple[Any, ...]:
  """
  Fingerprint via baked Codon ``.so`` (slot 0 in this process).

  Args:
    lines (list[str]): Stats lines.

  Returns:
    tuple[Any, ...]: ``(raw_stats, collapsed_rows, value_sum, proc_rows)``.

  Examples:
    >>> callable(codon_worker_fingerprint)
    True
  """
  _ensure_codon_on_path()
  mod = importlib.import_module("hpcperfstats_codon_parse")
  return mod.feed_and_collapse_fingerprint(list(lines), 0)


def codon_worker_parse(lines: list[str]) -> tuple[Any, Any]:
  """
  Full parse via baked Codon ``.so`` (slot 0 in this process).

  Args:
    lines (list[str]): Stats lines.

  Returns:
    tuple[Any, Any]: ``(stats_records, proc_rows)``.

  Examples:
    >>> callable(codon_worker_parse)
    True
  """
  _ensure_codon_on_path()
  mod = importlib.import_module("hpcperfstats_codon_parse")
  return mod.parse_stats_lines_codon(list(lines), 0)


def _recv(stdin: Any) -> Any:
  """
  Read one length-prefixed pickle frame from ``stdin``.

  Args:
    stdin (Any): File-like with ``.buffer`` (``sys.stdin``).

  Returns:
    Any: Unpickled request, or ``None`` on EOF/short read.

  Examples:
    >>> callable(_recv)
    True
  """
  raw_len = stdin.buffer.read(4)
  if not raw_len or len(raw_len) < 4:
    return None
  (n,) = struct.unpack("!I", raw_len)
  if n == 0:
    return None
  payload = stdin.buffer.read(n)
  if len(payload) < n:
    return None
  return pickle.loads(payload)  # noqa: S301 — trusted parent/child stdio


def _send(stdout: Any, obj: Any) -> None:
  """
  Write one length-prefixed pickle frame to ``stdout``.

  Args:
    stdout (Any): File-like with ``.buffer`` (``sys.stdout``).
    obj (Any): Picklable envelope.

  Returns:
    None: Always ``None``.

  Examples:
    >>> callable(_send)
    True
  """
  payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
  stdout.buffer.write(struct.pack("!I", len(payload)))
  stdout.buffer.write(payload)
  stdout.buffer.flush()


def main() -> int:
  """
  Stdio request loop: ``('fp'|'parse', lines)`` -> result pickle.

  Returns:
    int: Process exit code (``0``).

  Examples:
    >>> callable(main)
    True
  """
  _ensure_codon_on_path()
  while True:
    req = _recv(sys.stdin)
    if req is None:
      break
    try:
      kind, lines = req
      if kind == "fp":
        _send(sys.stdout, ("ok", codon_worker_fingerprint(list(lines))))
      elif kind == "parse":
        _send(sys.stdout, ("ok", codon_worker_parse(list(lines))))
      else:
        _send(sys.stdout, ("err", f"unknown kind={kind!r}"))
    except Exception as exc:
      _send(sys.stdout, ("err", f"{type(exc).__name__}: {exc}"))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
