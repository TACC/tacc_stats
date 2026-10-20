"""listend live path stamps shared-node dev and leaves exclusive rows alone."""

from hpcperfstats.dbload.lib.io_helpers import host_data_instance_from_stats_row
from hpcperfstats.dbload.lib.sync_timedb_parsing import DeltaCarryState
from hpcperfstats.dbload.lib.sync_timedb_sample_ingest import (
  ingest_monitor_sample_text,
)


def _host_rows(sample, schema):
  stats, proc = ingest_monitor_sample_text(
    sample,
    schema=schema,
    schema_fast=schema,
    carry=DeltaCarryState(),
  )
  assert proc.empty
  return [
    host_data_instance_from_stats_row(r) for r in stats.itertuples(index=False)
  ]


def test_listend_shared_sample_stamps_cpu_and_keeps_gpu_dev():
  schema = {"cpu": ["user", "sys"], "nvidia_gpu": ["util"]}
  sample = (
    "%jobs jids=job42\n"
    "%affinity jid=job42 cpus=0-1 gpus=0 cg=sched\n"
    "1710000001.0 job42 host.example.edu\n"
    "cpu 0 10 20\n"
    "cpu 1 5 6\n"
    "nvidia_gpu 0 9\n"
  )
  rows = _host_rows(sample, schema)
  by_type = {}
  for obj in rows:
    by_type.setdefault(obj.type, set()).add(obj.dev)
  assert by_type["cpu"] == {"j:job42"}
  assert by_type["nvidia_gpu"] == {"0"}
  assert all(obj.jid == "job42" for obj in rows)


def test_listend_exclusive_sample_dev_stays_empty():
  schema = {"cpu": ["user", "sys"]}
  sample = "1710000001.0 job42 host.example.edu\ncpu 0 10 20\n"
  rows = _host_rows(sample, schema)
  assert rows
  assert {obj.dev for obj in rows} == {""}
  assert {obj.jid for obj in rows} == {"job42"}
