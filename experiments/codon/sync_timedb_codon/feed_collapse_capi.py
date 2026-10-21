"""Codon-only C ABI for free-threaded pyext trampoline (``--lib`` build).

Not imported under CPython — ``@export`` / ``Ptr[cobj]`` are Codon constructs.
Built by ``build_codon_ext_in_pipeline.sh`` into ``libhpcperfstats_codon_kernel.so``.
"""

from typing import List

from feed_collapse import feed_and_collapse


@export
def feed_and_collapse_fingerprint_c(
    n: int,
    ptr: Ptr[cobj],
    out_raw: Ptr[int],
    out_collapsed: Ptr[int],
    out_value_sum: Ptr[float],
    out_proc_rows: Ptr[float],
):
  """C-ABI: ``n`` NUL-terminated UTF-8 strings at ``ptr`` (char**).

  Writes fingerprint into out_* (avoids Codon Tuple sret). Called from
  ``pyext_ft_init.c`` — Codon 0.20.4 ``--pyext`` from_python converters are
  GIL-ABI and fail on free-threaded 3.14t.
  """
  lines: List[str] = []
  i = 0
  while i < n:
    lines.append(str.from_ptr(ptr[i]))
    i += 1
  fp = feed_and_collapse(lines)
  out_raw[0] = fp[0]
  out_collapsed[0] = fp[1]
  out_value_sum[0] = fp[2]
  out_proc_rows[0] = fp[3]
