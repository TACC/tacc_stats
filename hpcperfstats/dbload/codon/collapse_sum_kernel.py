"""Extra Codon-NumPy kernel: fused float sum over a contiguous buffer.

Inventory maximize: compile-unit extract beyond feed_collapse (not a full
``sync_timedb_*.py`` rewrite). Used for compile inventory + optional A/B.
"""

import numpy as np


def fused_sum(values: list[float]) -> float:
  """Return ``np.add.reduce`` over ``values`` (0.0 when empty)."""
  n = len(values)
  if n == 0:
    return 0.0
  buf = np.zeros(n, dtype=float)
  for i in range(n):
    buf[i] = values[i]
  return float(np.add.reduce(buf))
