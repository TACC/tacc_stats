"""
Job-scoped ``host_data`` filter for shared-node co-tenant isolation.

Analysis aggregates must match ``LiveJidScopedDistinctHostTimeCount`` and
ingest stamps: rows belonging to a job have ``jid = <jid>`` (exclusive /
sole) or ``dev = 'j:' || <jid>`` (shared non-GPU / ``host_mem_job``).
GPU hardware ``dev`` stays numeric; optional ``job_affinity.gpu_list``
restricts which devices count for a job.

Attributes:
  SHARED_HOST_WIDE_HELP_FOOTER: User-facing red-footer copy for shared jobs.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q

SHARED_HOST_WIDE_HELP_FOOTER: str = (
  "This job ran on a shared node. CPU, GPU, and job memory are scoped to "
  "this job when affinity or cgroup data is available; some other counters "
  "may still be host-wide."
)


def job_dev_token(jid: str) -> str:
  """
  Return the ``host_data.dev`` stamp for a shared-node job id.

  Matches ingest ``shared_dev_for_row`` / ``job_dev_tokens`` truncation.

  Args:
    jid (str): Job id (accounting ``job_data.jid``).

  Returns:
    str: ``j:<jid>`` truncated to 64 characters.

  Examples:
    >>> job_dev_token("42")
    'j:42'
    >>> len(job_dev_token("x" * 80))
    64
  """
  return f"j:{jid!s}"[:64]


def job_host_data_scope_q(jid: str) -> Q:
  """
  Django ``Q`` matching job-owned ``host_data`` rows for one jid.

  Combines exclusive/sole rows (``jid`` column) with shared stamped rows
  (``dev = j:<jid>``). Combine with ``host__in`` and time filters in the
  same queryset; do not use alone for host-wide admin paths.

  Args:
    jid (str): Job id.

  Returns:
    Q: ``jid=<jid> OR dev=j:<jid>``.

  Examples:
    >>> str(job_host_data_scope_q("7"))
    "(OR: ('jid', '7'), ('dev', 'j:7'))"
  """
  jid_s = str(jid)
  return Q(jid=jid_s) | Q(dev=job_dev_token(jid_s))


def job_host_data_scope_sql(
  *,
  table_alias: str = "h",
  jid_param_placeholder: str = "%s",
) -> str:
  """
  SQL fragment ``(alias.jid = %s OR alias.dev = ('j:' || %s))``.

  Callers bind the same jid string twice (or use a single named param in
  dialects that support it). Empty alias uses bare column names.

  Args:
    table_alias (str): Table/alias prefix (default ``h``); empty for bare
      ``jid`` / ``dev``.
    jid_param_placeholder (str): Placeholder text for each bind (default
      ``%s``).

  Returns:
    str: Parenthesized SQL predicate.

  Examples:
    >>> job_host_data_scope_sql()
    "(h.jid = %s OR h.dev = ('j:' || %s))"
    >>> job_host_data_scope_sql(table_alias="")
    "(jid = %s OR dev = ('j:' || %s))"
  """
  prefix = f"{table_alias}." if table_alias else ""
  p = jid_param_placeholder
  return f"({prefix}jid = {p} OR {prefix}dev = ('j:' || {p}))"


def gpu_devs_for_job(
  jid: str,
  host: str | None = None,
) -> list[str] | None:
  """
  Hardware GPU ``dev`` values from ``job_affinity``, or ``None`` if unrestricted.

  When any affinity row exists for the jid (optionally narrowed to ``host``),
  return the union of ``gpu_list`` entries as strings. An empty list means
  the job has affinity but no GPUs (exclude all hardware GPU devices).
  When no affinity rows exist, return ``None`` (job owns the node / no
  restriction — keep all GPU ``dev`` values in the window).

  Args:
    jid (str): Job id.
    host (str | None): Optional hostname; when set, only that host's
      affinity row(s) are read.

  Returns:
    list[str] | None: Allowed ``dev`` strings, empty list, or ``None``.

  Examples:
    >>> gpu_devs_for_job("")  # doctest: +SKIP
    None
  """
  jid_s = str(jid or "").strip()
  if not jid_s:
    return None
  from hpcperfstats.site.lib.machine.models import job_affinity

  qs = job_affinity.objects.filter(jid=jid_s)
  if host:
    qs = qs.filter(host=str(host))
  lists = list(qs.values_list("gpu_list", flat=True))
  if not lists:
    return None
  out: list[str] = []
  seen: set[str] = set()
  for gl in lists:
    if not gl:
      continue
    for d in gl:
      s = str(d).strip()
      if not s or s in seen:
        continue
      seen.add(s)
      out.append(s)
  return out


def apply_job_host_data_scope(qs: Any, jid: str) -> Any:
  """
  Filter a ``host_data`` queryset to one job's rows.

  Args:
    qs (Any): Django queryset on ``host_data`` (or compatible).
    jid (str): Job id.

  Returns:
    Any: ``qs.filter(job_host_data_scope_q(jid))``.

  Examples:
    >>> apply_job_host_data_scope(None, "1")  # doctest: +SKIP
  """
  if not jid:
    return qs
  return qs.filter(job_host_data_scope_q(str(jid)))


def apply_gpu_affinity_dev_filter(
  qs: Any,
  jid: str,
  *,
  host: str | None = None,
  affinity_devs: list[str] | None = None,
) -> Any:
  """
  When affinity GPU lists exist, restrict ``dev__in`` to those devices.

  Pass ``affinity_devs`` to avoid repeated DB lookups (``None`` means
  look up; empty list means no GPUs allowed; non-empty restricts).

  Args:
    qs (Any): Django queryset already scoped to GPU types.
    jid (str): Job id.
    host (str | None): Optional host for affinity lookup.
    affinity_devs (list[str] | None): Precomputed ``gpu_devs_for_job``
      result; ``None`` triggers a lookup.

  Returns:
    Any: Filtered queryset, or ``qs`` unchanged when unrestricted.

  Examples:
    >>> apply_gpu_affinity_dev_filter(None, "1")  # doctest: +SKIP
  """
  devs = affinity_devs
  if devs is None:
    devs = gpu_devs_for_job(jid, host=host)
  if devs is None:
    return qs
  return qs.filter(dev__in=list(devs))


def job_is_shared_node_from_jobish(jobish: Any) -> bool:
  """
  Resolve ``is_shared_node`` from a job-like object with a ``jid`` attribute.

  Args:
    jobish (Any): Object or mapping with ``jid`` (``jid_table``, ``job_data``).

  Returns:
    bool: Shared-node signal when jid is a real string/int; else False.

  Examples:
    >>> job_is_shared_node_from_jobish(type("J", (), {"jid": ""})())
    False
  """
  jid = getattr(jobish, "jid", None)
  if jid is None and isinstance(jobish, dict):
    jid = jobish.get("jid")
  if not isinstance(jid, (str, int)):
    return False
  s = str(jid).strip()
  if not s:
    return False
  return job_is_shared_node(s)


def job_is_shared_node(jid: str) -> bool:
  """
  True when the job has ``job_affinity`` rows (affinity-only).

  Used for Job Detail ``is_shared_node`` and shared-job help footers.
  Does not probe ``host_data`` for ``dev=j:<jid>`` (that EXISTS timed out
  under portal load and flooded statement-timeout ERROR logs). Missing
  affinity → False (omit shared footer).

  Args:
    jid (str): Job id.

  Returns:
    bool: True when affinity rows exist for ``jid``; else False.

  Examples:
    >>> job_is_shared_node("")  # doctest: +SKIP
    False
  """
  jid_s = str(jid or "").strip()
  if not jid_s:
    return False
  from hpcperfstats.site.lib.machine.models import job_affinity

  return job_affinity.objects.filter(jid=jid_s).exists()
