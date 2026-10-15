#!/usr/bin/env python3
"""Seed one rank-0 job in dev DB for PGO soak discovery (empty-DB E2E only).

Attributes:
  PGO_SOAK_SEED_JID (str): Default ``job_data.jid`` for the synthetic soak job.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

PGO_SOAK_SEED_JID = "__pgo_soak_seed__"


def _django_setup() -> None:
  """Load project settings and initialize Django before ORM use.

  Returns:
    None

  Examples:
    >>> _django_setup()  # doctest: +SKIP
  """
  os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "hpcperfstats.site.hpcperfstats_site.settings",
  )
  import django

  django.setup()


def seed_rank0_job(
  *,
  jid: str = PGO_SOAK_SEED_JID,
  delete_existing: bool = True,
) -> str:
  """
  Insert or refresh a synthetic job that classifies as performance sort rank 0.

  Args:
    jid (str): Primary key for ``job_data``.
    delete_existing (bool): When true, remove prior seed rows for ``jid`` first.

  Returns:
    str: The jid written.

  Raises:
    RuntimeError: Rank is not 0 or plot artifacts are not ready after insert.

  Examples:
    >>> seed_rank0_job(
    ...   jid="__pgo_soak_seed__", delete_existing=False
    ... )  # doctest: +SKIP
  """
  _django_setup()
  from hpcperfstats.dbload.lib import conf_parser as cfg
  from hpcperfstats.site.lib.machine import (
    job_detail_artifacts as detail_cfg,
    job_plot_artifacts as plot_cfg,
  )
  from hpcperfstats.site.lib.machine.job_list_performance import (
    annotate_job_list_performance_fields,
  )
  from hpcperfstats.site.lib.machine.models import (
    job_data,
    job_detail_artifact,
    job_plot_artifact,
    metrics_data,
  )

  if delete_existing:
    job_data.objects.filter(jid=jid).delete()

  now = datetime.now(UTC)
  start = now - timedelta(hours=2)
  host_ext = cfg.get_host_name_ext()
  host = f"pgo-seed-node.{host_ext}" if host_ext else "pgo-seed-node.local"
  job_data.objects.create(
    jid=jid,
    submit_time=start,
    start_time=start,
    end_time=now,
    runtime=7200.0,
    username="__pgo_soak_automation__",
    account="pgo",
    queue="debug",
    state="COMPLETED",
    host_list=[host],
    metrics_distinct_time_count=10,
    host_data_schema_json={},
  )
  metrics_data.objects.create(
    jid_id=jid,
    type="cpu",
    metric="seed_metric",
    units="none",
    value=1.0,
  )

  job = job_data.objects.get(jid=jid)
  plot_fp = plot_cfg.compute_plot_input_fingerprint(job)
  detail_fp = detail_cfg.compute_detail_input_fingerprint(job)
  stub_item = {"pgo_soak_seed": True, "jid": jid}
  _raw, compressed, enc = plot_cfg.json_item_to_compressed_payload(stub_item)
  for kind in plot_cfg.JOB_PLOT_KINDS:
    job_plot_artifact.objects.update_or_create(
      jid=job,
      plot_kind=kind,
      layout=plot_cfg.JOB_PLOT_LAYOUT_NORMAL,
      defaults={
        "payload_compressed": compressed,
        "payload_encoding": enc,
        "input_fingerprint": plot_fp,
        "artifact_schema": plot_cfg.APP_PLOT_ARTIFACT_SCHEMA_VERSION,
      },
    )
  for kind in (
    detail_cfg.ARTIFACT_KIND_JOB_DETAIL,
    detail_cfg.ARTIFACT_KIND_MULTIPRECISION_MIX,
  ):
    job_detail_artifact.objects.update_or_create(
      jid=job,
      artifact_kind=kind,
      artifact_scope="",
      defaults={
        "payload_compressed": compressed,
        "payload_encoding": enc,
        "input_fingerprint": detail_fp,
        "artifact_schema": detail_cfg.APP_DETAIL_ARTIFACT_SCHEMA_VERSION,
      },
    )

  qs = annotate_job_list_performance_fields(job_data.objects.filter(jid=jid))
  row = qs.get()
  rank = int(row.performance_sort_rank)
  ready = bool(row.plots_artifacts_ready)
  if rank != 0 or not ready:
    raise RuntimeError(
      f"seed failed: performance_sort_rank={rank} plots_artifacts_ready={ready}",
    )
  return jid


def main(argv: list[str] | None = None) -> int:
  """
  CLI entry: seed rank-0 job and print jid on stdout.

  Args:
    argv: Optional argument vector (defaults to ``sys.argv[1:]``).

  Returns:
    Process exit code.

  Examples:
    >>> main([])  # doctest: +SKIP
  """
  parser = argparse.ArgumentParser(
    description="Seed rank-0 job for PGO soak E2E"
  )
  parser.add_argument(
    "--jid",
    default=PGO_SOAK_SEED_JID,
    help="job_data.jid to create (default: %(default)s)",
  )
  parser.add_argument(
    "--keep-existing",
    action="store_true",
    help="Do not delete existing rows for jid before insert",
  )
  args = parser.parse_args(argv)
  try:
    out_jid = seed_rank0_job(
      jid=args.jid, delete_existing=not args.keep_existing
    )
  except RuntimeError as exc:
    sys.stderr.write(f"{exc}\n")
    return 1
  print(f"pgo_soak_seed: jid={out_jid} rank0=ok")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
