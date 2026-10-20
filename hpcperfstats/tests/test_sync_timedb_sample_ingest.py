"""Shared monitor sample → dataframe ingest (listend + sync write stage)."""

from __future__ import annotations

from hpcperfstats.dbload.lib.io_helpers import host_data_instance_from_stats_row
from hpcperfstats.dbload.lib.sync_timedb_parsing import DeltaCarryState
from hpcperfstats.dbload.lib.sync_timedb_sample_ingest import (
  ingest_monitor_sample_text,
  sample_measurement_types,
  schema_covers_measurement_types,
)


def test_sample_measurement_types_and_schema_cover():
  sample = "1710000001.0 1 host.example.edu\ncpuuser - 1 2 3\nproc 1 2\n"
  assert sample_measurement_types(sample) == ["cpuuser", "proc"]
  assert schema_covers_measurement_types(
    {"cpuuser": ["a", "b", "c"]}, ["cpuuser", "proc"]
  )
  assert not schema_covers_measurement_types({}, ["cpuuser"])


def test_ingest_skips_without_schema():
  sample = "1710000001.0 1 host.example.edu\ncpuuser - 1 2 3\n"
  stats, proc = ingest_monitor_sample_text(
    sample,
    schema={},
    schema_fast={},
    carry=DeltaCarryState(),
  )
  assert stats.empty
  assert proc.empty


def test_ingest_sets_jid_from_header():
  schema = {"cpu": ["user", "sys"]}
  sample = "1710000001.0 job42 host.example.edu\ncpu 0 10 20\n"
  stats, proc = ingest_monitor_sample_text(
    sample,
    schema=schema,
    schema_fast=schema,
    carry=DeltaCarryState(),
  )
  assert not stats.empty
  assert proc.empty
  objs = [
    host_data_instance_from_stats_row(r) for r in stats.itertuples(index=False)
  ]
  assert objs
  assert all(o.jid == "job42" for o in objs)


def test_ingest_idle_jid_dash_maps_to_none():
  schema = {"cpu": ["user", "sys"]}
  sample = "1710000001.0 - host.example.edu\ncpu 0 10 20\n"
  stats, _ = ingest_monitor_sample_text(
    sample,
    schema=schema,
    schema_fast=schema,
    carry=DeltaCarryState(),
  )
  assert not stats.empty
  objs = [
    host_data_instance_from_stats_row(r) for r in stats.itertuples(index=False)
  ]
  assert objs
  assert all(o.jid is None for o in objs)
