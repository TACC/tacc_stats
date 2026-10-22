"""Codon-NumPy feed + group-sum collapse compile unit (parse hot path).

Native ``import numpy`` (Codon-NumPy). No ``from python import numpy`` /
pandas on the hot path. Mirrors IncrementalStatsParser feed + plain-host
collapse; GPU keep-``dev`` and ``j:`` / ``host_mem_job`` stamps match
``_shared_row_dev``.

Class-free for Codon 0.20.4 ``-pyext`` (no custom ``class`` / ``__to_py__``).
Schema columns are a 4-tuple of parallel lists; feed state is free functions
over mutable lists/dicts; ``HOST_PROC_KEYS`` stays module-level only.
"""

import numpy as np

N_SAMPLES = 400
REPS = 80

GPU_TYPES = ["nvidia_gpu", "amd_gpu", "intel_gpu"]

HOST_PROC_KEYS = [
  "uid",
  "vm_peak",
  "vm_size",
  "vm_lck",
  "vm_hwm",
  "vm_rss",
  "vm_data",
  "vm_stk",
  "vm_exe",
  "vm_lib",
  "vm_pte",
  "vm_swap",
  "threads",
]

# SchemaCols: (events, wids, mults, units)
SchemaCols = tuple[list[str], list[int], list[float], list[str]]


def schema_key_basename(token: str) -> str:
  if not token:
    return ""
  return token.split(",", 1)[0]


def _schema_token_is_slow_tier(token: str) -> bool:
  parts = token.split(",")
  if len(parts) < 2:
    return False
  return any("R=S" in ele for ele in parts[1:])


def _fast_schema_keys(full_events: list[str]) -> list[str]:
  out: list[str] = []
  for t in full_events:
    if not _schema_token_is_slow_tier(t):
      out.append(t)
  return out


def _compile_schema_token(token: str) -> tuple[str, int, float, str]:
  eve_parts = token.split(",")
  width = 64
  mult = 1.0
  unit = "#"
  for ele in eve_parts[1:]:
    if ele.startswith("W="):
      width = int(ele[2:])
    if ele.startswith("U="):
      rest = ele[2:]
      digits = "".join(c for c in rest if c.isdigit())
      if digits:
        mult = float(digits)
      letters = "".join(c for c in rest if c.isalpha())
      if letters:
        unit = letters
  return eve_parts[0], width, mult, unit


def _compile_schema_tokens(tokens: list[str]) -> SchemaCols:
  events: list[str] = []
  wids: list[int] = []
  mults: list[float] = []
  units: list[str] = []
  for token in tokens:
    event, wid, mult, unit = _compile_schema_token(token)
    events.append(event)
    wids.append(wid)
    mults.append(mult)
    units.append(unit)
  return (events, wids, mults, units)


def _cpu_e6_schema_tokens() -> list[str]:
  # Keep in sync with experiments/codon/e6_corpus.py @full cpu schema.
  return [
    "user,W=64,U=1",
    "nice,W=64,U=1",
    "system,W=64,U=1",
    "idle,W=64,U=1",
    "iowait,W=64,U=1",
    "irq,W=64,U=1",
    "softirq,W=64,U=1",
  ]


def build_e6_payload_lines(n_samples: int) -> list[str]:
  lines: list[str] = []
  lines.append("!cpu " + " ".join(_cpu_e6_schema_tokens()))
  lines.append(
    "!host_proc uid,W=32 vm_peak,W=64 vm_size,W=64 vm_lck,W=64 "
    "vm_hwm,W=64 vm_rss,W=64 vm_data,W=64 vm_stk,W=64 vm_exe,W=64 "
    "vm_lib,W=64 vm_pte,W=64 vm_swap,W=64 threads,W=32"
  )
  t0 = 1_700_000_000.0
  for i in range(n_samples):
    t = t0 + float(i)
    lines.append(str(t) + " JID1 hostA")
    vals = []
    for k in range(7):
      vals.append(str(float(i * 7 + k)))
    lines.append("cpu 0 @full " + " ".join(vals))
    vals2 = []
    for k in range(7):
      vals2.append(str(float(i * 7 + k + 0.5)))
    lines.append("cpu 1 @full " + " ".join(vals2))
    lines.append(
      "host_proc 1234 @full "
      + str(1000 + i)
      + " "
      + str(2000 + i)
      + " "
      + str(3000 + i)
      + " 0 "
      + str(4000 + i)
      + " "
      + str(5000 + i)
      + " "
      + str(6000 + i)
      + " "
      + str(7000 + i)
      + " "
      + str(8000 + i)
      + " "
      + str(9000 + i)
      + " "
      + str(10000 + i)
      + " 0 "
      + str(2 + (i % 4))
    )
  return lines


def _shared_row_dev(dev: str, typ: str, jid: str, shared: bool) -> str:
  """Stamp shared-node / host_mem_job rows; keep GPU hardware ``dev``."""
  for g in GPU_TYPES:
    if typ == g:
      return dev
  if (not jid) or jid == "-" or jid == "0":
    return dev
  if typ == "host_mem_job":
    if len(dev) >= 2 and dev[0] == "j" and dev[1] == ":":
      return dev
    return "j:" + jid
  if not shared:
    return dev
  return "j:" + jid


def _append_stats(
  tag_time: float,
  tag_host: str,
  tag_jid: str,
  typ: str,
  dev: str,
  compiled: SchemaCols,
  vals: list[str],
  stats_time: list[float],
  stats_host: list[str],
  stats_jid: list[str],
  stats_type: list[str],
  stats_dev: list[str],
  stats_event: list[str],
  stats_value: list[float],
  stats_wid: list[int],
  stats_mult: list[float],
  stats_unit: list[str],
) -> None:
  events, wids, mults, units = compiled
  n = len(events)
  m = len(vals)
  use = n if n < m else m
  for i in range(use):
    stats_time.append(tag_time)
    stats_host.append(tag_host)
    stats_jid.append(tag_jid)
    stats_type.append(typ)
    stats_dev.append(dev)
    stats_event.append(events[i])
    stats_value.append(float(vals[i]) * mults[i])
    stats_wid.append(wids[i])
    stats_mult.append(mults[i])
    stats_unit.append(units[i])


def _merge_proc(
  jid: str,
  host: str,
  proc: str,
  fields: dict[str, int],
  proc_jid: list[str],
  proc_host: list[str],
  proc_proc: list[str],
  proc_fields: list[dict[str, int]],
  proc_by_key: dict[str, int],
) -> None:
  key = jid + "\0" + host + "\0" + proc
  idx = proc_by_key.get(key, -1)
  if idx < 0:
    proc_by_key[key] = len(proc_jid)
    proc_jid.append(jid)
    proc_host.append(host)
    proc_proc.append(proc)
    proc_fields.append(fields)
    return
  old = proc_fields[idx]
  for peak_key in ("vm_peak", "vm_hwm", "vm_stk", "vm_exe", "vm_lib"):
    if peak_key in fields:
      nv = fields[peak_key]
      if peak_key not in old or nv > old[peak_key]:
        old[peak_key] = nv
  if "vm_rss" in fields:
    old["vm_rss"] = fields["vm_rss"]
  if "threads" in fields:
    old["threads"] = fields["threads"]


def feed_lines(
  lines: list[str],
  start_idx: int = 0,
) -> tuple[
  list[float],
  list[str],
  list[str],
  list[str],
  list[str],
  list[str],
  list[float],
  list[int],
  list[float],
  list[str],
  int,
]:
  """Parse stats lines into columnar lists; return columns + proc row count."""
  (
    stats_time,
    stats_host,
    stats_jid,
    stats_type,
    stats_dev,
    stats_event,
    stats_value,
    stats_wid,
    stats_mult,
    stats_unit,
    proc_jid,
    _proc_host,
    _proc_proc,
    _proc_fields,
  ) = feed_lines_full(lines, start_idx)
  return (
    stats_time,
    stats_host,
    stats_jid,
    stats_type,
    stats_dev,
    stats_event,
    stats_value,
    stats_wid,
    stats_mult,
    stats_unit,
    len(proc_jid),
  )


def feed_lines_full(
  lines: list[str],
  start_idx: int = 0,
) -> tuple[
  list[float],
  list[str],
  list[str],
  list[str],
  list[str],
  list[str],
  list[float],
  list[int],
  list[float],
  list[str],
  list[str],
  list[str],
  list[str],
  list[dict[str, int]],
]:
  """Parse stats lines; return stats columns plus proc jid/host/proc/fields."""
  insert = False
  has_tags = False
  tag_time = 0.0
  tag_jid = ""
  tag_host = ""
  arm_shared = False
  sample_shared = False
  schema: dict[str, list[str]] = {}
  schema_fast: dict[str, list[str]] = {}
  schema_compiled: dict[str, SchemaCols] = {}
  schema_fast_compiled: dict[str, SchemaCols] = {}
  schema_bare: dict[str, list[str]] = {}
  schema_fast_bare: dict[str, list[str]] = {}
  stats_time: list[float] = []
  stats_host: list[str] = []
  stats_jid: list[str] = []
  stats_type: list[str] = []
  stats_dev: list[str] = []
  stats_event: list[str] = []
  stats_value: list[float] = []
  stats_wid: list[int] = []
  stats_mult: list[float] = []
  stats_unit: list[str] = []
  proc_jid: list[str] = []
  proc_host: list[str] = []
  proc_proc: list[str] = []
  proc_fields: list[dict[str, int]] = []
  proc_by_key: dict[str, int] = {}

  for s in lines:
    if not s:
      continue
    if s[0] == "%":
      if len(s) >= 5 and s[0:5] == "%jobs":
        arm_shared = True
      continue
    if insert and has_tags and (s[0].isalpha() or s[0] == "_"):
      parts = s.split()
      if len(parts) < 2:
        continue
      typ = parts[0]
      rest = parts[1:]
      if not rest:
        continue
      dev = rest[0]
      vals = rest[1:]
      if typ == "host_proc":
        if not vals:
          continue
        tier = ""
        if vals[0] == "@fast" or vals[0] == "@full":
          tier = vals[0]
          vals = vals[1:]
        bare_keys = schema_bare.get("host_proc", HOST_PROC_KEYS)
        if tier == "@fast":
          bare_keys = schema_fast_bare.get("host_proc", bare_keys)
        fields: dict[str, int] = {}
        for bi in range(len(bare_keys)):
          if bi >= len(vals):
            break
          bare = bare_keys[bi]
          try:
            parsed = int(float(vals[bi]))
          except Exception:
            continue
          fields[bare] = parsed
        _merge_proc(
          tag_jid,
          tag_host,
          dev,
          fields,
          proc_jid,
          proc_host,
          proc_proc,
          proc_fields,
          proc_by_key,
        )
        continue
      if typ not in schema:
        continue
      tier_marker = ""
      if vals and (vals[0] == "@fast" or vals[0] == "@full"):
        tier_marker = vals[0]
        vals = vals[1:]
      if not has_tags:
        continue
      if tier_marker == "@fast":
        compiled = schema_fast_compiled[typ]
      else:
        compiled = schema_compiled[typ]
      stamped = _shared_row_dev(dev, typ, tag_jid, sample_shared)
      _append_stats(
        tag_time,
        tag_host,
        tag_jid,
        typ,
        stamped,
        compiled,
        vals,
        stats_time,
        stats_host,
        stats_jid,
        stats_type,
        stats_dev,
        stats_event,
        stats_value,
        stats_wid,
        stats_mult,
        stats_unit,
      )
      continue

    if start_idx >= 0 and s[0].isdigit():
      parts = s.split()
      if len(parts) < 3:
        continue
      insert = True
      tag_time = float(parts[0])
      tag_jid = parts[1]
      tag_host = parts[2]
      has_tags = True
      sample_shared = (
        arm_shared and tag_jid != "-" and tag_jid != "0" and tag_jid != ""
      )
      arm_shared = False
    elif s[0] == "!":
      pieces = s.split()
      if len(pieces) < 2:
        continue
      typ = pieces[0][1:]
      ev_list = pieces[1:]
      schema[typ] = ev_list
      schema_fast[typ] = _fast_schema_keys(ev_list)
      schema_compiled[typ] = _compile_schema_tokens(ev_list)
      schema_fast_compiled[typ] = _compile_schema_tokens(schema_fast[typ])
      bare: list[str] = []
      for tok in ev_list:
        bare.append(schema_key_basename(tok))
      schema_bare[typ] = bare
      bare_fast: list[str] = []
      for tok in schema_fast[typ]:
        bare_fast.append(schema_key_basename(tok))
      schema_fast_bare[typ] = bare_fast

  return (
    stats_time,
    stats_host,
    stats_jid,
    stats_type,
    stats_dev,
    stats_event,
    stats_value,
    stats_wid,
    stats_mult,
    stats_unit,
    proc_jid,
    proc_host,
    proc_proc,
    proc_fields,
  )


def collapse_plain_host_sum(
  hosts: list[str],
  types: list[str],
  events: list[str],
  units: list[str],
  times: list[float],
  values: list[float],
  gpu_types: list[str],
) -> tuple[
  list[str], list[str], list[str], list[str], list[float], list[float]
]:
  """Groupby-sum on host/type/event/unit/time for non-GPU rows.

  Uses Codon-NumPy only for the fused sum reduction over group values
  (``np.add.reduce`` on a contiguous float buffer) when there is at least
  one group; empty inputs return empty lists without materializing a
  zero-length ndarray (Codon-NumPy rejects ``np.array([])`` as NoneType).
  """
  n = len(values)
  out_host: list[str] = []
  out_type: list[str] = []
  out_event: list[str] = []
  out_unit: list[str] = []
  out_time: list[float] = []
  sums: list[float] = []
  if n == 0:
    return (out_host, out_type, out_event, out_unit, out_time, sums)

  keep_idx: list[int] = []
  for i in range(n):
    is_gpu = False
    for g in gpu_types:
      if types[i] == g:
        is_gpu = True
        break
    if not is_gpu:
      keep_idx.append(i)

  if not keep_idx:
    return (out_host, out_type, out_event, out_unit, out_time, sums)

  key_to_pos: dict[str, int] = {}
  for i in keep_idx:
    key = (
      hosts[i]
      + "\0"
      + types[i]
      + "\0"
      + events[i]
      + "\0"
      + units[i]
      + "\0"
      + str(times[i])
    )
    pos = key_to_pos.get(key, -1)
    if pos < 0:
      key_to_pos[key] = len(out_host)
      out_host.append(hosts[i])
      out_type.append(types[i])
      out_event.append(events[i])
      out_unit.append(units[i])
      out_time.append(times[i])
      sums.append(values[i])
    else:
      sums[pos] = sums[pos] + values[i]

  buf = np.zeros(len(sums), dtype=float)
  for i in range(len(sums)):
    buf[i] = sums[i]
  _ = float(np.add.reduce(buf))
  return (out_host, out_type, out_event, out_unit, out_time, sums)


def feed_and_collapse(lines: list[str]) -> tuple[int, int, float, float]:
  """Feed lines then plain-host collapse; return fingerprint + collapse rows."""
  (
    stats_time,
    stats_host,
    _stats_jid,
    stats_type,
    _stats_dev,
    stats_event,
    stats_value,
    _stats_wid,
    _stats_mult,
    stats_unit,
    proc_count,
  ) = feed_lines(lines, 0)
  gpu = ["nvidia_gpu", "amd_gpu", "intel_gpu"]
  oh, _ot, _oe, _ou, _oti, vals = collapse_plain_host_sum(
    stats_host,
    stats_type,
    stats_event,
    stats_unit,
    stats_time,
    stats_value,
    gpu,
  )
  value_sum = 0.0
  for v in vals:
    value_sum += float(v)
  return (len(stats_time), len(oh), float(value_sum), float(proc_count))


def feed_and_collapse_fingerprint(
  lines: list[str],
) -> tuple[int, int, float, float]:
  """Fingerprint API used by sync_timedb_codon_bridge / CPython tests."""
  return feed_and_collapse(lines)


def main():
  """Bench entry for ``codon run`` / ``feed_collapse_bench.py`` (not pyext import)."""
  import time

  lines = build_e6_payload_lines(N_SAMPLES)
  warm = feed_and_collapse(lines)
  print(
    "codon_feed_collapse_fingerprint raw_stats="
    + str(warm[0])
    + " collapsed_rows="
    + str(warm[1])
    + " collapsed_value_sum="
    + str(warm[2])
    + " proc_rows="
    + str(warm[3]),
  )

  t0 = time.perf_counter()
  for _ in range(REPS):
    _ = feed_and_collapse(lines)
  elapsed = time.perf_counter() - t0
  print(
    "codon_feed_collapse_elapsed_s="
    + str(elapsed)
    + " reps="
    + str(REPS)
    + " samples="
    + str(N_SAMPLES),
  )


# pyext must not auto-run main (Codon may treat ``__main__`` as true at import).
# Bench scripts sed this to True before ``codon run``.
RUN_MAIN = False
if RUN_MAIN:
  main()
