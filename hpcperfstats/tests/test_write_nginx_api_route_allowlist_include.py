"""Drift tests for nginx API route allowlist generation."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from hpcperfstats.tests.urlconf_route_catalog import EXPECTED_ROUTE_TEMPLATES


def _repo_root() -> Path:
  return Path(__file__).resolve().parents[2]


def _load_writer():
  path = (
    _repo_root()
    / "services-conf"
    / "write_nginx_api_route_allowlist_include.py"
  )
  name = "write_nginx_api_route_allowlist_include"
  spec = importlib.util.spec_from_file_location(name, path)
  assert spec and spec.loader
  mod = importlib.util.module_from_spec(spec)
  sys.modules[name] = mod
  spec.loader.exec_module(mod)
  return mod


def test_location_prefixes_collapse_jobs_converters():
  mod = _load_writer()
  prefixes = mod.location_prefixes_from_api_templates(
    [
      "api/jobs/",
      "api/jobs/<str:pk>/",
      "api/jobs/<str:pk>/plots/",
      "api/jobs/filter_options/",
      "api/schema/",
    ]
  )
  assert prefixes == ["/api/jobs/", "/api/schema/"]


def test_empty_templates_raises_on_render():
  mod = _load_writer()
  try:
    mod.render_nginx_api_route_allowlist([])
  except ValueError as exc:
    assert "empty" in str(exc).lower()
  else:
    raise AssertionError("expected ValueError for empty allowlist")


def test_committed_inc_matches_generator_from_catalog():
  mod = _load_writer()
  committed = (
    _repo_root() / "services-conf" / "nginx-api-route-allowlist.inc"
  ).read_text(encoding="utf-8")
  expected = mod.render_nginx_api_route_allowlist(
    mod.location_prefixes_from_api_templates(EXPECTED_ROUTE_TEMPLATES)
  )
  assert committed == expected


def test_all_api_catalog_templates_covered_by_prefixes():
  mod = _load_writer()
  prefixes = mod.location_prefixes_from_api_templates(EXPECTED_ROUTE_TEMPLATES)
  assert prefixes, "allowlist must not be empty"
  api_templates = [t for t in EXPECTED_ROUTE_TEMPLATES if t.startswith("api/")]
  assert api_templates
  for template in api_templates:
    path = "/" + template
    # Strip converters for coverage check against collapsed prefixes.
    path_no_conv = re.sub(r"<[^>]+>", "", path)
    path_no_conv = path_no_conv.replace("//", "/")
    covered = any(
      path_no_conv.startswith(prefix) or path.startswith(prefix)
      for prefix in prefixes
    )
    assert covered, f"{template!r} not covered by {prefixes}"


def test_probe_api_dot_env_not_covered_by_prefixes():
  mod = _load_writer()
  prefixes = mod.location_prefixes_from_api_templates(EXPECTED_ROUTE_TEMPLATES)
  probe = "/api/.env"
  assert not any(probe.startswith(prefix) for prefix in prefixes)
  # Positive control: a real job API path is covered by /api/jobs/.
  assert any("/api/jobs/abc/".startswith(prefix) for prefix in prefixes)


def test_write_include_round_trip(tmp_path):
  mod = _load_writer()
  out = tmp_path / "nginx-api-route-allowlist.inc"
  prefixes = mod.write_nginx_api_route_allowlist_include(
    templates=EXPECTED_ROUTE_TEMPLATES,
    out_path=out,
  )
  text = out.read_text(encoding="utf-8")
  assert "location ^~ /api/jobs/" in text
  assert "proxy_pass http://django_server;" in text
  assert prefixes == mod.location_prefixes_from_api_templates(
    EXPECTED_ROUTE_TEMPLATES
  )
