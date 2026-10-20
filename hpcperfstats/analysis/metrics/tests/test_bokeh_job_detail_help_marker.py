"""Regression tests for Job Detail Bokeh screen-space help marker."""

import html

from bokeh.embed import json_item
from bokeh.plotting import figure

from hpcperfstats.analysis.metrics.lib.job_host_data_scope import (
  SHARED_HOST_WIDE_HELP_FOOTER,
)
from hpcperfstats.analysis.metrics.lib.plot.bokeh_job_detail_help_marker import (
  add_job_detail_bokeh_help_marker,
)


def test_json_item_contains_screen_space_help_label():
  p = figure(width=200, height=150, x_range=(0, 10), y_range=(0, 10))
  p.line([1, 9], [1, 9])
  add_job_detail_bokeh_help_marker(
    p,
    "Test plot description for help hover.",
    "Optional researcher-facing line.",
  )
  payload = json_item(p)
  blob = str(payload)
  assert "?" in blob or "\\u003f" in blob
  # Label uses data coordinates at the hit corner (not clipped screen x=-10).
  assert '"x": -10' not in blob and "'x': -10" not in blob


def test_help_marker_appends_shared_node_footer_when_requested():
  p = figure(width=200, height=150, x_range=(0, 10), y_range=(0, 10))
  p.line([1, 9], [1, 9])
  add_job_detail_bokeh_help_marker(
    p,
    "Test plot description for help hover.",
    "Optional researcher-facing line.",
    is_shared_node=True,
  )
  blob = html.unescape(str(json_item(p)))
  assert SHARED_HOST_WIDE_HELP_FOOTER in blob


def test_help_marker_omits_shared_node_footer_by_default():
  p = figure(width=200, height=150, x_range=(0, 10), y_range=(0, 10))
  p.line([1, 9], [1, 9])
  add_job_detail_bokeh_help_marker(
    p,
    "Test plot description for help hover.",
    "Optional researcher-facing line.",
  )
  blob = html.unescape(str(json_item(p)))
  assert SHARED_HOST_WIDE_HELP_FOOTER not in blob
