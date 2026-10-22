"""Regression tests for DevPlot's shared-node Bokeh help-marker wiring.

Mirrors the ``SHARED_HOST_WIDE_HELP_FOOTER`` gate exercised for
``SummaryPlot``/``roofline`` in ``test_hover_tooltips.py`` and
``test_bokeh_job_detail_help_marker.py``, scoped to
``DevPlot.plot_metric`` (type-detail/device-data Bokeh help hover).
"""

import html
from unittest.mock import patch

import pandas as pd
from bokeh.models import HoverTool

from hpcperfstats.analysis.metrics.lib.job_host_data_scope import (
  SHARED_HOST_WIDE_HELP_FOOTER,
)
from hpcperfstats.analysis.metrics.lib.plot.devplot import DevPlot


class _TypeDetailProvider:
  jid = "12345"

  def __init__(self, type_name: str = "host_ib"):
    self.type_name = type_name


def _plot_metric_for_jid(is_shared: bool, type_name: str = "host_ib"):
  dp = DevPlot(_TypeDetailProvider(type_name), ["h1", "h2"])
  dp.hc = {"h1": "#111111", "h2": "#222222"}
  df = pd.DataFrame(
    {
      "time": [
        pd.Timestamp("2024-01-01 00:00:00+00:00"),
        pd.Timestamp("2024-01-01 00:00:00+00:00"),
      ],
      "host": ["h1", "h2"],
      "MBW_CHANNEL_0": [3.0, 4.0],
    }
  )
  with patch(
    "hpcperfstats.analysis.metrics.lib.plot.devplot.job_is_shared_node_from_jobish",
    return_value=is_shared,
  ):
    return dp.plot_metric(df, "MBW_CHANNEL_0", "GB/s")


def _help_hover_tip_text(plot) -> str:
  help_hovers = [
    t
    for t in plot.tools
    if isinstance(t, HoverTool)
    and isinstance(t.tooltips, str)
    and "max-width:28em" in t.tooltips
  ]
  assert len(help_hovers) == 1
  return html.unescape(help_hovers[0].tooltips)


def test_devplot_appends_shared_node_footer_for_residual_type():
  tip = _help_hover_tip_text(_plot_metric_for_jid(True, "host_ib"))
  assert SHARED_HOST_WIDE_HELP_FOOTER in tip


def test_devplot_omits_footer_for_job_scoped_type_when_shared():
  tip = _help_hover_tip_text(_plot_metric_for_jid(True, "host_cpu"))
  assert SHARED_HOST_WIDE_HELP_FOOTER not in tip


def test_devplot_omits_shared_node_footer_when_not_shared():
  tip = _help_hover_tip_text(_plot_metric_for_jid(False, "host_ib"))
  assert SHARED_HOST_WIDE_HELP_FOOTER not in tip
