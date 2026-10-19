"""host_mem_job ingest: always stamp dev=j:<jid>; never merge into host_mem."""

from __future__ import annotations

from hpcperfstats.dbload.lib.monitor_naming import canonical as canon, resolve
from hpcperfstats.dbload.lib.sync_timedb_parsing import (
  build_stats_dataframes,
  compute_deltas_and_arc,
  parse_stats_lines,
)

_SCHEMA = (
  "!host_mem_job mem_used,U=KB mem_peak,U=KB anon_pages,U=KB "
  "file_pages,U=KB mapped,U=KB dirty,U=KB writeback,U=KB page_tables,U=KB\n"
)
_HOST_MEM_SCHEMA = "!host_mem mem_total,U=KB mem_used,U=KB\n"


def _collapsed_rows(lines: list[str]) -> list[tuple[str, str, str, str, float]]:
  stats_list, proc_list = parse_stats_lines(lines, 0)
  stats_df, _proc_df = build_stats_dataframes(stats_list, proc_list)
  collapsed = compute_deltas_and_arc(stats_df)
  out: list[tuple[str, str, str, str, float]] = []
  for row in collapsed.itertuples(index=False):
    out.append(
      (
        str(row.type),
        str(row.dev),
        str(row.jid),
        str(row.event),
        float(row.value),
      )
    )
  return out


def test_host_mem_job_stamps_j_dev_with_jobs_mark():
  lines = [
    _SCHEMA,
    "%jobs jids=111\n",
    "1710000001.0 111 hosta\n",
    "host_mem_job 111 100 200 10 20 1 2 3 4\n",
  ]
  rows = _collapsed_rows(lines)
  mem = [r for r in rows if r[0] == "host_mem_job"]
  assert mem
  assert all(r[1] == "j:111" for r in mem)
  assert all(r[2] == "111" for r in mem)
  by_event = {r[3]: r[4] for r in mem}
  assert by_event["mem_used"] == 100.0
  assert by_event["mem_peak"] == 200.0
  assert by_event["page_tables"] == 4.0


def test_host_mem_job_stamps_without_jobs_mark_full_resource():
  """Sole full-resource: no %jobs; host_mem_job still gets j: stamp."""
  lines = [
    _SCHEMA,
    "1710000001.0 62909 hosta\n",
    "host_mem_job 62909 50 60 1 2 0 0 0 0\n",
  ]
  rows = _collapsed_rows(lines)
  mem = [r for r in rows if r[0] == "host_mem_job"]
  assert mem
  assert {r[1] for r in mem} == {"j:62909"}
  assert {r[2] for r in mem} == {"62909"}


def test_host_mem_job_idempotent_when_wire_already_j_prefixed():
  lines = [
    _SCHEMA,
    "1710000001.0 9 hosta\n",
    "host_mem_job j:9 1 2 0 0 0 0 0 0\n",
  ]
  rows = _collapsed_rows(lines)
  mem = [r for r in rows if r[0] == "host_mem_job"]
  assert mem
  assert {r[1] for r in mem} == {"j:9"}


def test_host_mem_job_multi_jid_keeps_separate_devs():
  lines = [
    _SCHEMA,
    "%jobs jids=111,222\n",
    "1710000001.0 111 hosta\n",
    "host_mem_job 111 10 11 0 0 0 0 0 0\n",
    "%jobs jids=111,222\n",
    "1710000001.0 222 hosta\n",
    "host_mem_job 222 20 21 0 0 0 0 0 0\n",
  ]
  rows = _collapsed_rows(lines)
  mem = [r for r in rows if r[0] == "host_mem_job" and r[3] == "mem_used"]
  assert ("host_mem_job", "j:111", "111", "mem_used", 10.0) in mem
  assert ("host_mem_job", "j:222", "222", "mem_used", 20.0) in mem


def test_idle_header_omits_useful_host_mem_job_stamp():
  lines = [
    _SCHEMA,
    "1710000001.0 - hosta\n",
    "host_mem_job - 1 2 0 0 0 0 0 0\n",
  ]
  rows = _collapsed_rows(lines)
  mem = [r for r in rows if r[0] == "host_mem_job"]
  assert not any(r[1].startswith("j:") for r in mem)


def test_host_mem_coexists_without_j_stamp():
  lines = [
    _HOST_MEM_SCHEMA,
    _SCHEMA,
    "1710000001.0 111 hosta\n",
    "host_mem 0 1000 500\n",
    "host_mem_job 111 50 60 0 0 0 0 0 0\n",
  ]
  rows = _collapsed_rows(lines)
  numa = [r for r in rows if r[0] == "host_mem"]
  job = [r for r in rows if r[0] == "host_mem_job"]
  assert numa
  assert all(r[1] == "" for r in numa)
  assert job
  assert all(r[1] == "j:111" for r in job)


def test_host_mem_type_names_excludes_host_mem_job():
  names = resolve.host_mem_type_names()
  assert "host_mem_job" not in names
  assert canon.HOST_MEM_TYPE in names
  assert canon.HOST_MEM_JOB_TYPE == "host_mem_job"
