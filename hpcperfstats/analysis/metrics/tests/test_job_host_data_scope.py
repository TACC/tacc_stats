"""Unit tests for job_host_data_scope (shared-node co-tenant filter)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.db.models import Q

from hpcperfstats.analysis.metrics.lib.job_host_data_scope import (
  SHARED_HOST_WIDE_HELP_FOOTER,
  apply_gpu_affinity_dev_filter,
  apply_job_host_data_scope,
  gpu_devs_for_job,
  job_dev_token,
  job_host_data_scope_q,
  job_host_data_scope_sql,
  job_is_shared_node,
)


def _job_bounds_row(
  *,
  t0: datetime | None = None,
  t1: datetime | None = None,
  use_telemetry: bool = True,
) -> dict:
  if t0 is None:
    t0 = datetime(2026, 10, 19, 20, 47, tzinfo=UTC)
  if t1 is None:
    t1 = datetime(2026, 10, 19, 20, 51, tzinfo=UTC)
  if use_telemetry:
    return {
      "start_time": t0,
      "end_time": t1,
      "telemetry_first_time": t0,
      "telemetry_last_time": t1,
    }
  return {
    "start_time": t0,
    "end_time": t1,
    "telemetry_first_time": None,
    "telemetry_last_time": None,
  }


def test_job_dev_token_truncates_to_64():
  assert job_dev_token("42") == "j:42"
  assert len(job_dev_token("x" * 80)) == 64
  assert job_dev_token("x" * 80).startswith("j:")


def test_job_host_data_scope_q_or_jid_and_j_dev():
  q = job_host_data_scope_q("99")
  assert isinstance(q, Q)
  children = list(q.children)
  assert ("jid", "99") in children
  assert ("dev", "j:99") in children
  assert q.connector == Q.OR


def test_job_host_data_scope_sql_fragment():
  assert job_host_data_scope_sql() == ("(h.jid = %s OR h.dev = ('j:' || %s))")
  assert job_host_data_scope_sql(table_alias="") == (
    "(jid = %s OR dev = ('j:' || %s))"
  )


def test_apply_job_host_data_scope_filters_queryset():
  qs = MagicMock()
  qs.filter.return_value = "scoped"
  out = apply_job_host_data_scope(qs, "7")
  assert out == "scoped"
  args, _kwargs = qs.filter.call_args
  assert len(args) == 1
  assert isinstance(args[0], Q)
  assert ("jid", "7") in args[0].children
  assert ("dev", "j:7") in args[0].children


def test_apply_job_host_data_scope_empty_jid_passthrough():
  qs = MagicMock()
  assert apply_job_host_data_scope(qs, "") is qs
  qs.filter.assert_not_called()


def test_gpu_devs_for_job_none_when_no_affinity():
  with patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja:
    ja.objects.filter.return_value.values_list.return_value = []
    assert gpu_devs_for_job("1") is None


def test_gpu_devs_for_job_unions_lists():
  with patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja:
    qs = MagicMock()
    ja.objects.filter.return_value = qs
    qs.filter.return_value = qs
    qs.values_list.return_value = [["0", "1"], ["1", "2"]]
    assert gpu_devs_for_job("1", host="n0") == ["0", "1", "2"]


def test_gpu_devs_for_job_empty_list_when_affinity_no_gpus():
  with patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja:
    ja.objects.filter.return_value.values_list.return_value = [[], None]
    assert gpu_devs_for_job("1") == []


def test_apply_gpu_affinity_dev_filter_unrestricted():
  with patch(
    "hpcperfstats.analysis.metrics.lib.job_host_data_scope.gpu_devs_for_job",
    return_value=None,
  ):
    qs = MagicMock()
    assert apply_gpu_affinity_dev_filter(qs, "1") is qs
    assert apply_gpu_affinity_dev_filter(qs, "1", affinity_devs=None) is qs


def test_apply_gpu_affinity_dev_filter_restricts():
  qs = MagicMock()
  qs.filter.return_value = "gpu_scoped"
  out = apply_gpu_affinity_dev_filter(qs, "1", affinity_devs=["0"])
  assert out == "gpu_scoped"
  qs.filter.assert_called_once_with(dev__in=["0"])


def test_job_is_shared_node_affinity_or_j_dev():
  bounds = _job_bounds_row()
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
    patch("hpcperfstats.site.lib.machine.models.job_data") as jd,
  ):
    ja.objects.filter.return_value.exists.return_value = True
    assert job_is_shared_node("5") is True
    hd.objects.filter.assert_not_called()

    ja.objects.filter.return_value.exists.return_value = False
    jd.objects.filter.return_value.values.return_value.first.return_value = (
      bounds
    )
    hd.objects.filter.return_value.exists.return_value = True
    assert job_is_shared_node("5") is True
    kwargs = hd.objects.filter.call_args.kwargs
    assert kwargs["dev"] == "j:5"
    assert kwargs["time__gte"] == bounds["telemetry_first_time"]
    assert kwargs["time__lte"] == bounds["telemetry_last_time"]

    hd.objects.filter.return_value.exists.return_value = False
    assert job_is_shared_node("5") is False


def test_job_is_shared_node_missing_job_data_or_bounds_false():
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
    patch("hpcperfstats.site.lib.machine.models.job_data") as jd,
  ):
    ja.objects.filter.return_value.exists.return_value = False
    jd.objects.filter.return_value.values.return_value.first.return_value = None
    assert job_is_shared_node("5") is False
    hd.objects.filter.assert_not_called()

    jd.objects.filter.return_value.values.return_value.first.return_value = {
      "start_time": None,
      "end_time": None,
      "telemetry_first_time": None,
      "telemetry_last_time": None,
    }
    assert job_is_shared_node("5") is False
    hd.objects.filter.assert_not_called()


def test_job_is_shared_node_uses_start_end_when_telemetry_null():
  bounds = _job_bounds_row(use_telemetry=False)
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
    patch("hpcperfstats.site.lib.machine.models.job_data") as jd,
  ):
    ja.objects.filter.return_value.exists.return_value = False
    jd.objects.filter.return_value.values.return_value.first.return_value = (
      bounds
    )
    hd.objects.filter.return_value.exists.return_value = True
    assert job_is_shared_node("9") is True
    kwargs = hd.objects.filter.call_args.kwargs
    assert kwargs["time__gte"] == bounds["start_time"]
    assert kwargs["time__lte"] == bounds["end_time"]


def test_job_is_shared_node_database_error_fail_open():
  bounds = _job_bounds_row()
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
    patch("hpcperfstats.site.lib.machine.models.job_data") as jd,
  ):
    ja.objects.filter.return_value.exists.return_value = False
    jd.objects.filter.return_value.values.return_value.first.return_value = (
      bounds
    )
    hd.objects.filter.return_value.exists.side_effect = DatabaseError("cancel")
    assert job_is_shared_node("5") is False


def test_shared_host_wide_help_footer_copy():
  assert "shared node" in SHARED_HOST_WIDE_HELP_FOOTER.lower()
  assert "host-wide" in SHARED_HOST_WIDE_HELP_FOOTER.lower()


def test_co_tenant_q_excludes_other_job_children():
  """Job A's scope Q must not match job B's jid or j:dev alone."""
  qa = job_host_data_scope_q("A")
  qb = job_host_data_scope_q("B")
  a_vals = {c[1] for c in qa.children}
  b_vals = {c[1] for c in qb.children}
  assert "A" in a_vals and "j:A" in a_vals
  assert "B" in b_vals and "j:B" in b_vals
  assert a_vals.isdisjoint(b_vals)
