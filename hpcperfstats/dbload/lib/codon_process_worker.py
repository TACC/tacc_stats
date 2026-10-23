"""Minimal spawn-worker / Popen server for Codon parse (no Django imports).

Used both as:
- picklable callables for unit tests (rare), and
- ``python -m hpcperfstats.dbload.lib.codon_process_worker`` stdio servers
  (one codonrt per OS process; parent SIGKILLs on shutdown).

IPC is length-prefixed binary (version + kind/status + nbytes + payload).
Requests carry raw UTF-8 line blobs; parse responses use compact UTF-8 JSON
(stdlib ``json`` only — third-party binary packs that touch the GIL are
forbidden on 3.14t); fingerprint responses use ``struct "!iidd"``.

Attributes:
  CODON_PARSE_DIR: Baked pyext directory (``/opt/hpcperfstats/codon_parse``).
  PROTO_VER: Wire-protocol version (mismatch fail-closed).
  KIND_FP: Request kind for fingerprint.
  KIND_PARSE: Request kind for full parse.
  STATUS_OK: Response status success.
  STATUS_ERR: Response status error.
  FP_STRUCT: Fingerprint payload packer.
  _REQ_HDR: Request frame header (``!BBI`` ver/kind/nbytes).
  _RESP_HDR: Response frame header (``!BBI`` ver/status/nbytes).
"""

from __future__ import annotations

import importlib
import json
import os
import struct
import sys
from typing import Any

CODON_PARSE_DIR = "/opt/hpcperfstats/codon_parse"
PROTO_VER = 1
KIND_FP = 1
KIND_PARSE = 2
STATUS_OK = 0
STATUS_ERR = 1
FP_STRUCT = struct.Struct("!iidd")
_REQ_HDR = struct.Struct("!BBI")
_RESP_HDR = struct.Struct("!BBI")


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


def encode_request(kind: str, lines: list[str]) -> bytes:
  """
  Encode one parent→child request frame (header + UTF-8 body).

  Args:
    kind (str): ``fp`` or ``parse``.
    lines (list[str]): Stats lines (joined with ``\\n``).

  Returns:
    bytes: Wire bytes including ``PROTO_VER`` header.

  Raises:
    ValueError: When ``kind`` is not ``fp`` or ``parse``.

  Examples:
    >>> encode_request("fp", ["a"])[:2]
    b'\\x01\\x01'
  """
  if kind == "fp":
    kind_b = KIND_FP
  elif kind == "parse":
    kind_b = KIND_PARSE
  else:
    raise ValueError(f"unknown codon ipc kind={kind!r}")
  body = "\n".join(lines).encode("utf-8")
  return _REQ_HDR.pack(PROTO_VER, kind_b, len(body)) + body


def decode_request(frame: bytes) -> tuple[str, list[str]]:
  """
  Decode one request frame into ``(kind, lines)``.

  Args:
    frame (bytes): Full request including header.

  Returns:
    tuple[str, list[str]]: Kind and split lines.

  Raises:
    RuntimeError: On version/kind/length mismatch.
    ValueError: When header is truncated.

  Examples:
    >>> decode_request(encode_request("parse", ["x", "y"]))
    ('parse', ['x', 'y'])
  """
  if len(frame) < _REQ_HDR.size:
    raise ValueError("codon ipc request truncated")
  ver, kind_b, n = _REQ_HDR.unpack_from(frame, 0)
  if ver != PROTO_VER:
    raise RuntimeError(f"codon ipc version mismatch: {ver}")
  body = frame[_REQ_HDR.size : _REQ_HDR.size + n]
  if len(body) != n:
    raise RuntimeError("codon ipc request body short")
  if kind_b == KIND_FP:
    kind = "fp"
  elif kind_b == KIND_PARSE:
    kind = "parse"
  else:
    raise RuntimeError(f"codon ipc unknown kind={kind_b}")
  if n == 0:
    return kind, []
  return kind, body.decode("utf-8").split("\n")


def encode_response_ok(kind: str, body: Any) -> bytes:
  """
  Encode a successful child→parent response for ``kind``.

  Args:
    kind (str): ``fp`` or ``parse``.
    body (Any): Fingerprint 4-tuple or ``(stats, procs)`` parse pair.

  Returns:
    bytes: Wire bytes including ``PROTO_VER`` header.

  Raises:
    ValueError: When ``kind`` is unknown.

  Examples:
    >>> len(encode_response_ok("fp", (1, 1, 0.0, 0.0))) > 6
    True
  """
  if kind == "fp":
    raw_stats, collapsed_rows, value_sum, proc_rows = body
    payload = FP_STRUCT.pack(
      int(raw_stats),
      int(collapsed_rows),
      float(value_sum),
      float(proc_rows),
    )
  elif kind == "parse":
    # JSON only — avoid third-party C extensions that re-enable the GIL.
    payload = json.dumps(
      body, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
  else:
    raise ValueError(f"unknown codon ipc kind={kind!r}")
  return _RESP_HDR.pack(PROTO_VER, STATUS_OK, len(payload)) + payload


def encode_response_err(message: str) -> bytes:
  """
  Encode an error child→parent response.

  Args:
    message (str): UTF-8 error text.

  Returns:
    bytes: Wire bytes including ``PROTO_VER`` header.

  Examples:
    >>> encode_response_err("x")[1]
    1
  """
  payload = message.encode("utf-8")
  return _RESP_HDR.pack(PROTO_VER, STATUS_ERR, len(payload)) + payload


def decode_response(kind: str, frame: bytes) -> Any:
  """
  Decode one response frame for the request ``kind``.

  Args:
    kind (str): ``fp`` or ``parse`` (selects payload layout).
    frame (bytes): Full response including header.

  Returns:
    Any: Fingerprint 4-tuple or parse ``(stats, procs)``.

  Raises:
    RuntimeError: On version/status/length errors or worker err payload.
    ValueError: When header is truncated.

  Examples:
    >>> decode_response("fp", encode_response_ok("fp", (1, 2, 3.0, 4.0)))
    (1, 2, 3.0, 4.0)
  """
  if len(frame) < _RESP_HDR.size:
    raise ValueError("codon ipc response truncated")
  ver, status, n = _RESP_HDR.unpack_from(frame, 0)
  if ver != PROTO_VER:
    raise RuntimeError(f"codon ipc version mismatch: {ver}")
  payload = frame[_RESP_HDR.size : _RESP_HDR.size + n]
  if len(payload) != n:
    raise RuntimeError("codon ipc response body short")
  if status == STATUS_ERR:
    raise RuntimeError(payload.decode("utf-8", errors="replace"))
  if status != STATUS_OK:
    raise RuntimeError(f"codon ipc unknown status={status}")
  if kind == "fp":
    if len(payload) != FP_STRUCT.size:
      raise RuntimeError("codon ipc fp payload size mismatch")
    return FP_STRUCT.unpack(payload)
  if kind == "parse":
    return json.loads(payload.decode("utf-8"))
  raise ValueError(f"unknown codon ipc kind={kind!r}")


def _recv_frame(stdin: Any, hdr_size: int) -> bytes | None:
  """
  Read one length-prefixed frame (``!BBI`` header + body) from ``stdin``.

  Args:
    stdin (Any): File-like with ``.buffer`` (``sys.stdin``).
    hdr_size (int): Header byte count (``_REQ_HDR.size`` / ``_RESP_HDR.size``).

  Returns:
    bytes | None: Full frame, or ``None`` on EOF/short read.

  Examples:
    >>> callable(_recv_frame)
    True
  """
  raw_hdr = stdin.buffer.read(hdr_size)
  if not raw_hdr or len(raw_hdr) < hdr_size:
    return None
  _ver, _kind_or_status, n = struct.unpack_from("!BBI", raw_hdr, 0)
  body = stdin.buffer.read(n) if n else b""
  if len(body) < n:
    return None
  return raw_hdr + body


def _send_frame(stdout: Any, frame: bytes) -> None:
  """
  Write one complete frame to ``stdout`` and flush.

  Args:
    stdout (Any): File-like with ``.buffer`` (``sys.stdout``).
    frame (bytes): Encoded request or response.

  Returns:
    None: Always ``None``.

  Examples:
    >>> callable(_send_frame)
    True
  """
  stdout.buffer.write(frame)
  stdout.buffer.flush()


def main() -> int:
  """
  Stdio request loop: binary ``fp``/``parse`` frames → binary responses.

  Returns:
    int: Process exit code (``0``).

  Examples:
    >>> callable(main)
    True
  """
  _ensure_codon_on_path()
  while True:
    frame = _recv_frame(sys.stdin, _REQ_HDR.size)
    if frame is None:
      break
    try:
      kind, lines = decode_request(frame)
      if kind == "fp":
        _send_frame(
          sys.stdout,
          encode_response_ok("fp", codon_worker_fingerprint(list(lines))),
        )
      else:
        _send_frame(
          sys.stdout,
          encode_response_ok("parse", codon_worker_parse(list(lines))),
        )
    except Exception as exc:
      _send_frame(
        sys.stdout,
        encode_response_err(f"{type(exc).__name__}: {exc}"),
      )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
