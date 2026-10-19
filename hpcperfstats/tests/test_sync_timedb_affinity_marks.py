"""Archive streaming ingest keeps per-jid dev stamps across chunk flushes."""

from hpcperfstats.dbload.lib.sync_timedb_parsing import (
  DeltaCarryState,
  build_stats_dataframes,
  compute_deltas_and_arc_chunk,
  parse_stats_file_streaming_incremental,
)


def test_streaming_incremental_keeps_two_jids_at_one_second(tmp_path):
  body = (
    "!cpu user sys\n"
    "%jobs jids=123,456\n"
    "1710000001.0 123 hosta\n"
    "cpu 0 10 1\n"
    "%jobs jids=123,456\n"
    "1710000001.0 456 hosta\n"
    "cpu 0 30 3\n"
  )
  path = tmp_path / "stats"
  path.write_text(body)
  carry = DeltaCarryState()
  seen = []

  def on_chunk(stats_payload, proc_payload):
    stats_df, _proc_df = build_stats_dataframes(stats_payload, proc_payload)
    if stats_df.empty:
      return
    collapsed = compute_deltas_and_arc_chunk(stats_df, carry=carry)
    for row in collapsed.itertuples(index=False):
      seen.append((str(row.jid), str(row.dev)))

  parse_stats_file_streaming_incremental(
    str(path),
    flush_rows=1,
    on_chunk=on_chunk,
  )
  assert ("123", "j:123") in seen
  assert ("456", "j:456") in seen
  assert all(dev != "" for _jid, dev in seen)
