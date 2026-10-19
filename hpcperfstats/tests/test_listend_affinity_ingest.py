"""listend live path stamps shared-node dev and leaves exclusive rows alone."""

from hpcperfstats.dbload.lib.listend_db_ingest import _process_sample_to_orm
from hpcperfstats.dbload.lib.sync_timedb_parsing import DeltaCarryState


def _host_rows(sample, schema):
  host_objs, proc_objs = _process_sample_to_orm(
    sample,
    host="host.example.edu",
    schema=schema,
    schema_fast=schema,
    carry=DeltaCarryState(),
  )
  assert proc_objs == []
  return host_objs


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
