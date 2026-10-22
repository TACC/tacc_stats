"""Codon-only C ABI for free-threaded pyext trampoline (``--lib`` build).

Not imported under CPython — ``@export`` / ``Ptr[cobj]`` are Codon constructs.
Built by Dockerfile ``codon-build`` / ``build_codon_ext.sh`` into
``libhpcperfstats_codon_kernel.so``.
"""

from feed_collapse import HOST_PROC_KEYS, feed_and_collapse, feed_lines_full

_cache_time: list[float] = []
_cache_host: list[str] = []
_cache_jid: list[str] = []
_cache_type: list[str] = []
_cache_dev: list[str] = []
_cache_event: list[str] = []
_cache_value: list[float] = []
_cache_wid: list[int] = []
_cache_mult: list[float] = []
_cache_unit: list[str] = []
_cache_proc_jid: list[str] = []
_cache_proc_host: list[str] = []
_cache_proc_proc: list[str] = []
_cache_proc_fields: list[dict[str, int]] = []


def _lines_from_ptr(n: int, ptr: Ptr[cobj]) -> list[str]:
  lines: list[str] = []
  i = 0
  while i < n:
    lines.append(str.from_ptr(ptr[i]))
    i += 1
  return lines


@export
def feed_and_collapse_fingerprint_c(
  n: int,
  ptr: Ptr[cobj],
  out_raw: Ptr[int],
  out_collapsed: Ptr[int],
  out_value_sum: Ptr[float],
  out_proc_rows: Ptr[float],
):
  """C-ABI fingerprint (avoids Codon Tuple sret)."""
  lines = _lines_from_ptr(n, ptr)
  fp = feed_and_collapse(lines)
  out_raw[0] = fp[0]
  out_collapsed[0] = fp[1]
  out_value_sum[0] = fp[2]
  out_proc_rows[0] = fp[3]


@export
def parse_stats_lines_codon_run_c(
  n: int,
  ptr: Ptr[cobj],
  out_ns: Ptr[int],
  out_np: Ptr[int],
):
  """Feed lines into module cache; write stats/proc counts."""
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
  lines = _lines_from_ptr(n, ptr)
  (
    _cache_time,
    _cache_host,
    _cache_jid,
    _cache_type,
    _cache_dev,
    _cache_event,
    _cache_value,
    _cache_wid,
    _cache_mult,
    _cache_unit,
    _cache_proc_jid,
    _cache_proc_host,
    _cache_proc_proc,
    _cache_proc_fields,
  ) = feed_lines_full(lines, 0)
  out_ns[0] = len(_cache_time)
  out_np[0] = len(_cache_proc_jid)


@export
def pss_time_c(i: int) -> float:
  return _cache_time[i]


@export
def pss_value_c(i: int) -> float:
  return _cache_value[i]


@export
def pss_wid_c(i: int) -> int:
  return _cache_wid[i]


@export
def pss_mult_c(i: int) -> float:
  return _cache_mult[i]


@export
def pss_host_c(i: int) -> str:
  return _cache_host[i]


@export
def pss_jid_c(i: int) -> str:
  return _cache_jid[i]


@export
def pss_type_c(i: int) -> str:
  return _cache_type[i]


@export
def pss_dev_c(i: int) -> str:
  return _cache_dev[i]


@export
def pss_event_c(i: int) -> str:
  return _cache_event[i]


@export
def pss_unit_c(i: int) -> str:
  return _cache_unit[i]


@export
def psp_jid_c(i: int) -> str:
  return _cache_proc_jid[i]


@export
def psp_host_c(i: int) -> str:
  return _cache_proc_host[i]


@export
def psp_proc_c(i: int) -> str:
  return _cache_proc_proc[i]


@export
def psp_field_c(i: int, key_idx: int) -> int:
  """Return host_proc field or -1 when absent (key_idx indexes HOST_PROC_KEYS)."""
  if key_idx < 0 or key_idx >= len(HOST_PROC_KEYS):
    return -1
  key = HOST_PROC_KEYS[key_idx]
  fields = _cache_proc_fields[i]
  if key in fields:
    return fields[key]
  return -1
