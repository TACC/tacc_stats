"""Unit tests for job_host_data_scope (shared-node co-tenant filter)."""

from unittest.mock import MagicMock, patch

from django.db.models import Q

from hpcperfstats.analysis.metrics.lib.job_host_data_scope import (
  SHARED_HOST_WIDE_HELP_FOOTER,
  apply_gpu_affinity_dev_filter,
  apply_job_host_data_scope,
  apply_job_or_host_wide_scope,
  gpu_devs_for_job,
  host_wide_residual_ht_cache_key,
  is_job_scoped_host_data_type,
  job_dev_token,
  job_host_data_scope_q,
  job_host_data_scope_sql,
  job_is_shared_node,
  show_shared_host_wide_help_footer,
  use_host_wide_residual_scope,
)


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


def test_job_is_shared_node_affinity_true():
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
  ):
    ja.objects.filter.return_value.exists.return_value = True
    assert job_is_shared_node("5") is True
    hd.objects.filter.assert_not_called()


def test_job_is_shared_node_affinity_miss_no_host_data_sql():
  with (
    patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja,
    patch("hpcperfstats.site.lib.machine.models.host_data") as hd,
    patch("hpcperfstats.site.lib.machine.models.job_data") as jd,
  ):
    ja.objects.filter.return_value.exists.return_value = False
    assert job_is_shared_node("5") is False
    hd.objects.filter.assert_not_called()
    jd.objects.filter.assert_not_called()


def test_job_is_shared_node_empty_jid():
  with patch("hpcperfstats.site.lib.machine.models.job_affinity") as ja:
    assert job_is_shared_node("") is False
    assert job_is_shared_node("   ") is False
    ja.objects.filter.assert_not_called()


def test_shared_host_wide_help_footer_copy():
  text = SHARED_HOST_WIDE_HELP_FOOTER.lower()
  assert "shared node" in text or "node-wide" in text
  assert "host-level" in text or "host-wide" in text or "node-wide" in text
  assert (
    "disambiguat" in text or "not job-scoped" in text or "node-wide" in text
  )


def test_is_job_scoped_host_data_type_allowlist():
  assert is_job_scoped_host_data_type("host_cpu") is True
  assert is_job_scoped_host_data_type("nvidia_gpu") is True
  assert is_job_scoped_host_data_type("host_mem_job") is True
  assert is_job_scoped_host_data_type("host_mem") is False
  assert is_job_scoped_host_data_type("host_ib") is False
  assert is_job_scoped_host_data_type("") is False


def test_apply_job_or_host_wide_scope_shared_residual_skips_jid():
  qs = MagicMock()
  out = apply_job_or_host_wide_scope(qs, "7", "host_mem", shared=True)
  assert out is qs
  qs.filter.assert_not_called()


def test_apply_job_or_host_wide_scope_shared_cpu_scopes():
  qs = MagicMock()
  qs.filter.return_value = "scoped"
  out = apply_job_or_host_wide_scope(qs, "7", "host_cpu", shared=True)
  assert out == "scoped"
  qs.filter.assert_called_once()


def test_use_host_wide_residual_scope_and_footer_gate():
  assert use_host_wide_residual_scope("host_mem", shared=True) is True
  assert use_host_wide_residual_scope("host_cpu", shared=True) is False
  assert (
    show_shared_host_wide_help_footer(is_shared_node=True, typ="host_cpu")
    is False
  )
  assert (
    show_shared_host_wide_help_footer(is_shared_node=True, typ="host_mem")
    is True
  )
  assert (
    show_shared_host_wide_help_footer(is_shared_node=False, typ="host_mem")
    is False
  )


def test_host_wide_residual_ht_cache_key_omits_jid():
  key = host_wide_residual_ht_cache_key("h1,h2", "host_mem", "2026-10-22")
  assert "host_wide_residual_ht" in key
  assert "jid" not in key.lower().split("host_wide_residual_ht")[0]
  assert ":7:" not in key
  assert "host_mem" in key
  assert "2026-10-22" in key


def test_co_tenant_q_excludes_other_job_children():
  """Job A's scope Q must not match job B's jid or j:dev alone."""
  qa = job_host_data_scope_q("A")
  qb = job_host_data_scope_q("B")
  a_vals = {c[1] for c in qa.children}
  b_vals = {c[1] for c in qb.children}
  assert "A" in a_vals and "j:A" in a_vals
  assert "B" in b_vals and "j:B" in b_vals
  assert a_vals.isdisjoint(b_vals)
