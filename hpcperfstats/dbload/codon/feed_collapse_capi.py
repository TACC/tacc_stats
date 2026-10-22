"""Codon-only C ABI for free-threaded pyext trampoline (``--lib`` build).

Not imported under CPython — ``@export`` / ``Ptr[cobj]`` are Codon constructs.
Built by Dockerfile ``codon-build`` / ``build_codon_ext.sh`` into
``libhpcperfstats_codon_kernel.so``.

Per-slot cache banks (``MAX_CODON_SLOTS``) isolate concurrent callers under
bridge per-slot locks. Slot id is passed on every run/read export.
"""

from feed_collapse import HOST_PROC_KEYS, feed_and_collapse, feed_lines_full

MAX_CODON_SLOTS = 32

_cache_time: list[list[float]] = []
_cache_host: list[list[str]] = []
_cache_jid: list[list[str]] = []
_cache_type: list[list[str]] = []
_cache_dev: list[list[str]] = []
_cache_event: list[list[str]] = []
_cache_value: list[list[float]] = []
_cache_wid: list[list[int]] = []
_cache_mult: list[list[float]] = []
_cache_unit: list[list[str]] = []
_cache_proc_jid: list[list[str]] = []
_cache_proc_host: list[list[str]] = []
_cache_proc_proc: list[list[str]] = []
_cache_proc_fields: list[list[dict[str, int]]] = []
_banks_ready: int = 0


def _ensure_slot_banks() -> None:
  """Allocate empty per-slot cache banks once."""
  global _cache_time
  global _cache_host
  global _cache_jid
  global _cache_type
  global _cache_dev
  global _cache_event
  global _cache_value
  global _cache_wid
  global _cache_mult
  global _cache_unit
  global _cache_proc_jid
  global _cache_proc_host
  global _cache_proc_proc
  global _cache_proc_fields
  global _banks_ready
  if _banks_ready == 1:
    return
  _cache_time = []
  _cache_host = []
  _cache_jid = []
  _cache_type = []
  _cache_dev = []
  _cache_event = []
  _cache_value = []
  _cache_wid = []
  _cache_mult = []
  _cache_unit = []
  _cache_proc_jid = []
  _cache_proc_host = []
  _cache_proc_proc = []
  _cache_proc_fields = []
  i = 0
  while i < MAX_CODON_SLOTS:
    empty_f: list[float] = []
    _cache_time.append(empty_f)
    empty_f2: list[float] = []
    _cache_value.append(empty_f2)
    empty_f3: list[float] = []
    _cache_mult.append(empty_f3)
    empty_s1: list[str] = []
    _cache_host.append(empty_s1)
    empty_s2: list[str] = []
    _cache_jid.append(empty_s2)
    empty_s3: list[str] = []
    _cache_type.append(empty_s3)
    empty_s4: list[str] = []
    _cache_dev.append(empty_s4)
    empty_s5: list[str] = []
    _cache_event.append(empty_s5)
    empty_s6: list[str] = []
    _cache_unit.append(empty_s6)
    empty_i1: list[int] = []
    _cache_wid.append(empty_i1)
    empty_s7: list[str] = []
    _cache_proc_jid.append(empty_s7)
    empty_s8: list[str] = []
    _cache_proc_host.append(empty_s8)
    empty_s9: list[str] = []
    _cache_proc_proc.append(empty_s9)
    empty_d1: list[dict[str, int]] = []
    _cache_proc_fields.append(empty_d1)
    i += 1
  _banks_ready = 1


def _lines_from_ptr(n: int, ptr: Ptr[cobj]) -> list[str]:
  lines: list[str] = []
  i = 0
  while i < n:
    lines.append(str.from_ptr(ptr[i]))
    i += 1
  return lines


@export
def feed_and_collapse_fingerprint_c(
  slot: int,
  n: int,
  ptr: Ptr[cobj],
  out_raw: Ptr[int],
  out_collapsed: Ptr[int],
  out_value_sum: Ptr[float],
  out_proc_rows: Ptr[float],
):
  """C-ABI fingerprint (avoids Codon Tuple sret). Slot-scoped; caller locks."""
  _ensure_slot_banks()
  if slot < 0 or slot >= MAX_CODON_SLOTS:
    out_raw[0] = 0
    out_collapsed[0] = 0
    out_value_sum[0] = 0.0
    out_proc_rows[0] = 0.0
    return
  lines = _lines_from_ptr(n, ptr)
  fp = feed_and_collapse(lines)
  out_raw[0] = fp[0]
  out_collapsed[0] = fp[1]
  out_value_sum[0] = fp[2]
  out_proc_rows[0] = fp[3]


@export
def parse_stats_lines_codon_run_c(
  slot: int,
  n: int,
  ptr: Ptr[cobj],
  out_ns: Ptr[int],
  out_np: Ptr[int],
):
  """Feed lines into slot cache bank; write stats/proc counts."""
  global _cache_time
  global _cache_host
  global _cache_jid
  global _cache_type
  global _cache_dev
  global _cache_event
  global _cache_value
  global _cache_wid
  global _cache_mult
  global _cache_unit
  global _cache_proc_jid
  global _cache_proc_host
  global _cache_proc_proc
  global _cache_proc_fields
  _ensure_slot_banks()
  if slot < 0 or slot >= MAX_CODON_SLOTS:
    out_ns[0] = 0
    out_np[0] = 0
    return
  lines = _lines_from_ptr(n, ptr)
  (
    _cache_time[slot],
    _cache_host[slot],
    _cache_jid[slot],
    _cache_type[slot],
    _cache_dev[slot],
    _cache_event[slot],
    _cache_value[slot],
    _cache_wid[slot],
    _cache_mult[slot],
    _cache_unit[slot],
    _cache_proc_jid[slot],
    _cache_proc_host[slot],
    _cache_proc_proc[slot],
    _cache_proc_fields[slot],
  ) = feed_lines_full(lines, 0)
  out_ns[0] = len(_cache_time[slot])
  out_np[0] = len(_cache_proc_jid[slot])


@export
def pss_time_c(slot: int, i: int) -> float:
  return _cache_time[slot][i]


@export
def pss_value_c(slot: int, i: int) -> float:
  return _cache_value[slot][i]


@export
def pss_wid_c(slot: int, i: int) -> int:
  return _cache_wid[slot][i]


@export
def pss_mult_c(slot: int, i: int) -> float:
  return _cache_mult[slot][i]


@export
def pss_host_c(slot: int, i: int) -> str:
  return _cache_host[slot][i]


@export
def pss_jid_c(slot: int, i: int) -> str:
  return _cache_jid[slot][i]


@export
def pss_type_c(slot: int, i: int) -> str:
  return _cache_type[slot][i]


@export
def pss_dev_c(slot: int, i: int) -> str:
  return _cache_dev[slot][i]


@export
def pss_event_c(slot: int, i: int) -> str:
  return _cache_event[slot][i]


@export
def pss_unit_c(slot: int, i: int) -> str:
  return _cache_unit[slot][i]


@export
def psp_jid_c(slot: int, i: int) -> str:
  return _cache_proc_jid[slot][i]


@export
def psp_host_c(slot: int, i: int) -> str:
  return _cache_proc_host[slot][i]


@export
def psp_proc_c(slot: int, i: int) -> str:
  return _cache_proc_proc[slot][i]


@export
def psp_field_c(slot: int, i: int, key_idx: int) -> int:
  """Return host_proc field or -1 when absent (key_idx indexes HOST_PROC_KEYS)."""
  if key_idx < 0 or key_idx >= len(HOST_PROC_KEYS):
    return -1
  key = HOST_PROC_KEYS[key_idx]
  fields = _cache_proc_fields[slot][i]
  if key in fields:
    return fields[key]
  return -1


# Eager once-init under single-threaded import before concurrent native entry.
_ensure_slot_banks()
