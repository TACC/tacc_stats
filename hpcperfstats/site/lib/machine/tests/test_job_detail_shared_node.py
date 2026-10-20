"""job_detail exposes is_shared_node from job_is_shared_node(jid) (no live DB)."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from hpcperfstats.site.lib.machine import cache_utils as cu

pytestmark = pytest.mark.machine_unit_mock


def _patch_job_detail_for_shared_node(api_module, jid, is_shared):
  """Return context manager that stubs job_detail dependencies (no ORM)."""
  mock_j = MagicMock()
  mock_j.acct_host_list = ["n1.example.com"]
  mock_j.schema = {}
  mock_j.get_llite_delta_by_event.return_value = MagicMock(empty=True)
  t0 = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
  mock_j.start_time = t0
  mock_j.end_time = t0

  job_mock = MagicMock()
  job_mock.jid = jid
  job_mock.username = "u1"
  job_mock.start_time = t0
  job_mock.end_time = t0

  def cached_se(key, timeout, fn):
    if key.startswith(f"{cu.KEY_JOB}:"):
      return job_mock
    if key.startswith(f"{cu.KEY_GPU_AGG}:"):
      return None
    if key.startswith(f"{cu.KEY_GPU_COUNT}:"):
      return None
    if key.startswith(f"{cu.KEY_PROC_LIST}:"):
      return []
    return fn()

  vis_qs = MagicMock()
  vis_qs.exists.return_value = True

  return (
    patch.object(api_module, "_require_auth", return_value=None),
    patch.object(
      api_module, "_apply_non_staff_job_visibility", return_value=vis_qs
    ),
    patch.object(
      api_module, "get_site_content_cache_timeout", return_value=3600
    ),
    patch.object(api_module, "build_job_metrics_display_list", return_value=[]),
    patch.object(api_module, "load_job_detail_artifact", return_value={}),
    patch.object(
      api_module, "compute_detail_input_fingerprint", return_value="fp"
    ),
    patch.object(api_module.cfg, "get_xalt_user", return_value=""),
    patch.object(api_module.cfg, "get_host_name_ext", return_value=""),
    patch.object(api_module, "cached_orm", side_effect=cached_se),
    patch.object(
      api_module,
      "_job_for_detail_list_serializer",
      return_value=job_mock,
    ),
    patch.object(
      api_module,
      "JobListSerializer",
      return_value=MagicMock(data={"jid": jid, "username": "u1"}),
    ),
    patch.object(api_module, "local_timezone", UTC),
    patch.object(api_module, "job_is_shared_node", return_value=is_shared),
  )


def _run_job_detail(api_module, jid, is_shared, is_staff=False):
  factory = RequestFactory()
  request = factory.get(f"/api/jobs/{jid}/")
  request.session = {"username": "u1", "is_staff": is_staff}

  ctx = _patch_job_detail_for_shared_node(api_module, jid, is_shared)
  with ThreadPoolExecutor(max_workers=4) as executor, ExitStack() as stack:
    stack.enter_context(
      patch.object(api_module, "_get_small_executor", return_value=executor)
    )
    for cm in ctx:
      stack.enter_context(cm)
    return api_module.job_detail(request, jid)


def test_job_detail_reports_is_shared_node_true():
  """Shared-node jobs (job_affinity rows or dev=j:<jid>) report is_shared_node=True."""
  from hpcperfstats.site.lib.machine import api

  response = _run_job_detail(api, "test-shared-node-true", True)

  assert response.status_code == 200
  assert response.data["is_shared_node"] is True


def test_job_detail_reports_is_shared_node_false():
  """Exclusive/sole jobs report is_shared_node=False (no host-wide help footer)."""
  from hpcperfstats.site.lib.machine import api

  response = _run_job_detail(api, "test-shared-node-false", False)

  assert response.status_code == 200
  assert response.data["is_shared_node"] is False
