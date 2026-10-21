"""Codon-NumPy feed + group-sum collapse compile unit (parse hot path).

Native ``import numpy`` (Codon-NumPy). No ``from python import numpy`` /
pandas on the hot path. Mirrors IncrementalStatsParser feed + the plain
host groupby-sum branch of ``_collapse_stats_with_deltas`` (GPU / ``j:``
paths stay on CPython until parity locks them).
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

N_SAMPLES = 400
REPS = 80

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


def schema_key_basename(token: str) -> str:
  if not token:
    return ""
  return token.split(",", 1)[0]


def _schema_token_is_slow_tier(token: str) -> bool:
  parts = token.split(",")
  if len(parts) < 2:
    return False
  for ele in parts[1:]:
    if "R=S" in ele:
      return True
  return False


def _fast_schema_keys(full_events: List[str]) -> List[str]:
  out: List[str] = []
  for t in full_events:
    if not _schema_token_is_slow_tier(t):
      out.append(t)
  return out


def _compile_schema_token(token: str) -> Tuple[str, int, float, str]:
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


class CompiledSchema:
  events: List[str]
  wids: List[int]
  mults: List[float]
  units: List[str]

  def __init__(self):
    self.events = []
    self.wids = []
    self.mults = []
    self.units = []


def _compile_schema_tokens(tokens: List[str]) -> CompiledSchema:
  out = CompiledSchema()
  for token in tokens:
    event, wid, mult, unit = _compile_schema_token(token)
    out.events.append(event)
    out.wids.append(wid)
    out.mults.append(mult)
    out.units.append(unit)
  return out


class ProcRow:
  jid: str
  host: str
  proc: str
  uid: Optional[int]
  vm_peak: Optional[int]
  vm_size: Optional[int]
  vm_lck: Optional[int]
  vm_hwm: Optional[int]
  vm_rss: Optional[int]
  vm_data: Optional[int]
  vm_stk: Optional[int]
  vm_exe: Optional[int]
  vm_lib: Optional[int]
  vm_pte: Optional[int]
  vm_swap: Optional[int]
  threads: Optional[int]

  def __init__(self):
    self.jid = ""
    self.host = ""
    self.proc = ""
    self.uid = None
    self.vm_peak = None
    self.vm_size = None
    self.vm_lck = None
    self.vm_hwm = None
    self.vm_rss = None
    self.vm_data = None
    self.vm_stk = None
    self.vm_exe = None
    self.vm_lib = None
    self.vm_pte = None
    self.vm_swap = None
    self.threads = None


def _cpu_e6_schema_tokens() -> List[str]:
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


def build_e6_payload_lines(n_samples: int) -> List[str]:
  lines: List[str] = []
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
    # Second device -> collapse must sum across dev for non-GPU.
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


class FeedKernel:
  start_idx: int
  insert: bool
  has_tags: bool
  tag_time: float
  tag_jid: str
  tag_host: str
  schema: Dict[str, List[str]]
  schema_fast: Dict[str, List[str]]
  schema_compiled: Dict[str, CompiledSchema]
  schema_fast_compiled: Dict[str, CompiledSchema]
  schema_bare: Dict[str, List[str]]
  schema_fast_bare: Dict[str, List[str]]
  stats_time: List[float]
  stats_host: List[str]
  stats_jid: List[str]
  stats_type: List[str]
  stats_dev: List[str]
  stats_event: List[str]
  stats_value: List[float]
  stats_wid: List[int]
  stats_mult: List[float]
  stats_unit: List[str]
  proc_rows: List[ProcRow]
  _proc_by_key: Dict[str, int]

  def __init__(self, start_idx: int):
    self.start_idx = start_idx
    self.insert = False
    self.has_tags = False
    self.tag_time = 0.0
    self.tag_jid = ""
    self.tag_host = ""
    self.schema = {}
    self.schema_fast = {}
    self.schema_compiled = {}
    self.schema_fast_compiled = {}
    self.schema_bare = {}
    self.schema_fast_bare = {}
    self.stats_time = []
    self.stats_host = []
    self.stats_jid = []
    self.stats_type = []
    self.stats_dev = []
    self.stats_event = []
    self.stats_value = []
    self.stats_wid = []
    self.stats_mult = []
    self.stats_unit = []
    self.proc_rows = []
    self._proc_by_key = {}

  def _compiled_schema_for(self, typ: str, fast: bool) -> CompiledSchema:
    if fast:
      return self.schema_fast_compiled[typ]
    return self.schema_compiled[typ]

  def _append_stats(
      self, typ: str, dev: str, compiled: CompiledSchema, vals: List[str]
  ):
    n = len(compiled.events)
    m = len(vals)
    use = n if n < m else m
    for i in range(use):
      self.stats_time.append(self.tag_time)
      self.stats_host.append(self.tag_host)
      self.stats_jid.append(self.tag_jid)
      self.stats_type.append(typ)
      self.stats_dev.append(dev)
      self.stats_event.append(compiled.events[i])
      self.stats_value.append(float(vals[i]) * compiled.mults[i])
      self.stats_wid.append(compiled.wids[i])
      self.stats_mult.append(compiled.mults[i])
      self.stats_unit.append(compiled.units[i])

  def _merge_proc(self, row: ProcRow):
    key = row.jid + "\0" + row.host + "\0" + row.proc
    idx = self._proc_by_key.get(key, -1)
    if idx < 0:
      self._proc_by_key[key] = len(self.proc_rows)
      self.proc_rows.append(row)
      return
    old = self.proc_rows[idx]
    if row.vm_peak is not None:
      if old.vm_peak is None or row.vm_peak > old.vm_peak:
        old.vm_peak = row.vm_peak
    if row.vm_hwm is not None:
      if old.vm_hwm is None or row.vm_hwm > old.vm_hwm:
        old.vm_hwm = row.vm_hwm
    if row.vm_stk is not None:
      if old.vm_stk is None or row.vm_stk > old.vm_stk:
        old.vm_stk = row.vm_stk
    if row.vm_exe is not None:
      if old.vm_exe is None or row.vm_exe > old.vm_exe:
        old.vm_exe = row.vm_exe
    if row.vm_lib is not None:
      if old.vm_lib is None or row.vm_lib > old.vm_lib:
        old.vm_lib = row.vm_lib
    if row.vm_rss is not None:
      old.vm_rss = row.vm_rss
    if row.threads is not None:
      old.threads = row.threads

  def feed_line(self, s: str):
    if not s:
      return
    i = self.start_idx
    if self.insert and self.has_tags:
      if s[0].isalpha() or s[0] == "_":
        parts = s.split()
        if len(parts) < 2:
          return
        typ = parts[0]
        rest = parts[1:]
        if not rest:
          return
        dev = rest[0]
        vals = rest[1:]
        if typ == "host_proc":
          if not vals:
            return
          tier = ""
          if vals[0] == "@fast" or vals[0] == "@full":
            tier = vals[0]
            vals = vals[1:]
          bare_keys = self.schema_bare.get("host_proc", HOST_PROC_KEYS)
          if tier == "@fast":
            bare_keys = self.schema_fast_bare.get("host_proc", bare_keys)
          row = ProcRow()
          row.jid = self.tag_jid
          row.host = self.tag_host
          row.proc = dev
          for bi in range(len(bare_keys)):
            if bi >= len(vals):
              break
            bare = bare_keys[bi]
            try:
              parsed = int(float(vals[bi]))
            except Exception:
              continue
            if bare == "uid":
              row.uid = parsed
            elif bare == "vm_peak":
              row.vm_peak = parsed
            elif bare == "vm_size":
              row.vm_size = parsed
            elif bare == "vm_lck":
              row.vm_lck = parsed
            elif bare == "vm_hwm":
              row.vm_hwm = parsed
            elif bare == "vm_rss":
              row.vm_rss = parsed
            elif bare == "vm_data":
              row.vm_data = parsed
            elif bare == "vm_stk":
              row.vm_stk = parsed
            elif bare == "vm_exe":
              row.vm_exe = parsed
            elif bare == "vm_lib":
              row.vm_lib = parsed
            elif bare == "vm_pte":
              row.vm_pte = parsed
            elif bare == "vm_swap":
              row.vm_swap = parsed
            elif bare == "threads":
              row.threads = parsed
          self._merge_proc(row)
          return
        if typ not in self.schema:
          return
        tier_marker = ""
        if vals and (vals[0] == "@fast" or vals[0] == "@full"):
          tier_marker = vals[0]
          vals = vals[1:]
        if not self.has_tags:
          return
        compiled = self._compiled_schema_for(typ, tier_marker == "@fast")
        self._append_stats(typ, dev, compiled, vals)
        return

    if i >= self.start_idx and s[0].isdigit():
      parts = s.split()
      if len(parts) < 3:
        return
      self.insert = True
      self.tag_time = float(parts[0])
      self.tag_jid = parts[1]
      self.tag_host = parts[2]
      self.has_tags = True
    elif s[0] == "!":
      pieces = s.split()
      if len(pieces) < 2:
        return
      typ = pieces[0][1:]
      ev_list = pieces[1:]
      self.schema[typ] = ev_list
      self.schema_fast[typ] = _fast_schema_keys(ev_list)
      self.schema_compiled[typ] = _compile_schema_tokens(ev_list)
      self.schema_fast_compiled[typ] = _compile_schema_tokens(
          self.schema_fast[typ],
      )
      bare: List[str] = []
      for tok in ev_list:
        bare.append(schema_key_basename(tok))
      self.schema_bare[typ] = bare
      bare_fast: List[str] = []
      for tok in self.schema_fast[typ]:
        bare_fast.append(schema_key_basename(tok))
      self.schema_fast_bare[typ] = bare_fast

  def feed_lines(self, lines: List[str]):
    for line in lines:
      self.feed_line(line)

  def stats_len(self) -> int:
    return len(self.stats_time)


def collapse_plain_host_sum(
    hosts: List[str],
    types: List[str],
    events: List[str],
    units: List[str],
    times: List[float],
    values: List[float],
    gpu_types: List[str],
) -> Tuple[List[str], List[str], List[str], List[str], List[float], List[float]]:
  """Groupby-sum on host/type/event/unit/time for non-GPU rows.

  Uses Codon-NumPy only for the fused sum reduction over group values
  (``np.add.reduce`` on a contiguous float buffer) when there is at least
  one group; empty inputs return empty lists without materializing a
  zero-length ndarray (Codon-NumPy rejects ``np.array([])`` as NoneType).
  """
  n = len(values)
  out_host: List[str] = []
  out_type: List[str] = []
  out_event: List[str] = []
  out_unit: List[str] = []
  out_time: List[float] = []
  sums: List[float] = []
  if n == 0:
    return (out_host, out_type, out_event, out_unit, out_time, sums)

  keep_idx: List[int] = []
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

  key_to_pos: Dict[str, int] = {}
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

  # Codon-NumPy touch: fused total over collapsed values (compile path proof).
  buf = np.zeros(len(sums), dtype=float)
  for i in range(len(sums)):
    buf[i] = sums[i]
  _ = float(np.add.reduce(buf))
  return (out_host, out_type, out_event, out_unit, out_time, sums)


def feed_and_collapse(lines: List[str]) -> Tuple[int, int, float, float]:
  """Feed lines then plain-host collapse; return fingerprint + collapse rows."""
  k = FeedKernel(0)
  k.feed_lines(lines)
  gpu = ["nvidia_gpu", "amd_gpu", "intel_gpu"]
  oh, ot, oe, ou, oti, vals = collapse_plain_host_sum(
      k.stats_host,
      k.stats_type,
      k.stats_event,
      k.stats_unit,
      k.stats_time,
      k.stats_value,
      gpu,
  )
  value_sum = 0.0
  for v in vals:
    value_sum += float(v)
  return (len(k.stats_time), len(oh), float(value_sum), float(len(k.proc_rows)))


def feed_and_collapse_fingerprint(
    lines: List[str],
) -> Tuple[int, int, float, float]:
  """pyext alias used by sync_timedb_codon_bridge."""
  return feed_and_collapse(lines)


def main():
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


if __name__ == "__main__":
  main()
