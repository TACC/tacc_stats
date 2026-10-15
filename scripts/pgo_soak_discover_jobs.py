#!/usr/bin/env python3
"""Run inside web container: rank-0 job list via local gunicorn (no proxy redirect)."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta


def main() -> int:
  """
  Query rank-0 jobs via local gunicorn and print JSON jids on stdout.

  Returns:
    int: Zero on success.

  Examples:
    >>> main()  # doctest: +SKIP
  """
  os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "hpcperfstats.site.hpcperfstats_site.settings",
  )
  import django

  django.setup()
  raw = os.environ.get("HPC_PGO_SOAK_RAW_API_KEY", "").strip()
  if not raw:
    sys.stderr.write(
      "pgo_soak_discover_jobs: HPC_PGO_SOAK_RAW_API_KEY required\n"
    )
    return 1

  list_days = int(os.environ.get("HPC_PGO_SOAK_JOB_LIST_DAYS", "30"))
  allow_metrics = os.environ.get("HPC_PGO_SOAK_ALLOW_METRICS_ONLY", "") == "1"
  now = datetime.now(UTC)
  gte = (now - timedelta(days=list_days)).isoformat()
  lte = (now + timedelta(hours=1)).isoformat()
  ranks = ["0"]
  if allow_metrics:
    ranks.append("1")

  seen: set[str] = set()
  jids: list[str] = []
  for rank in ranks:
    query = urllib.parse.urlencode(
      {
        "performance_sort_rank": rank,
        "end_time__gte": gte,
        "end_time__lte": lte,
      },
    )
    url = f"http://127.0.0.1:8000/api/jobs/?{query}"
    req = urllib.request.Request(
      url,
      headers={
        "Accept": "application/json",
        "X-API-Key": raw,
      },
      method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
      payload = json.loads(resp.read().decode("utf-8"))
    for row in payload.get("job_list") or []:
      jid = row.get("jid")
      if jid and jid not in seen:
        seen.add(jid)
        jids.append(str(jid))

  sys.stdout.write(json.dumps({"jids": jids}) + "\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
