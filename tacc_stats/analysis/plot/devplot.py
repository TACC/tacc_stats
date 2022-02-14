#!/usr/bin/env python3
import psycopg2
import os, sys, stat
from multiprocessing import Pool
from datetime import datetime, timedelta
import time, string
from pandas import DataFrame, to_datetime, Timedelta, concat, read_sql
import pandas
from bokeh.palettes import d3
from bokeh.layouts import gridplot
from bokeh.models import HoverTool, ColumnDataSource, Range1d
from bokeh.models.glyphs import Step
from bokeh.plotting import figure

class DevPlot():

  def __init__(self, conn, host_list):
    self.conn = conn
    self.host_list = host_list

  def plot_metric(self, df, event, unit = None):
    s = time.time()

    df = df[["time", "host", event]]
    plot = figure(plot_width=400, plot_height=150, x_axis_type = "datetime",
                  y_range = Range1d(-0.1, 1.1*df[event].max()), y_axis_label = event + ' ' + unit)

    for h in self.host_list:
      source = ColumnDataSource(df[df.host == h])
      plot.add_glyph(source, Step(x = "time", y = event, mode = "before", line_color = self.hc[h]))
    print("time to plot {0}: {1}".format(event, time.time() -s))
    return plot

  def plot(self):

    self.hc = {}
    colors = d3["Category20"][20]
    for i, hostname in enumerate(self.host_list):
      self.hc[hostname] = colors[i%20]

    print("Host Count:", len(self.host_list))

    df = read_sql("select host, time from type_detail group by host, time order by host, time", self.conn)
    event_df = read_sql("""select distinct on (event) event,unit from type_detail where host = '{}'""".format(next(iter(self.host_list))), self.conn)
    event_list = event_df[["event", "unit"]].values
    #event_list = list(sorted(event_df[["event", "unit"]].values))
    #unit_list = list(sorted(event_df["unit"].values))
    #print(event_list,unit_list)
    type_df = read_sql("""select distinct on (type) type from type_detail where host = '{}'""".format(next(iter(self.host_list))), self.conn)
    type_list = list(sorted(type_df["type"].values))

    metric = "arc"
    if "mem" in type_list: metric = "value"

    for event, unit in event_list:
      s = time.time()
      df[event] = read_sql("select sum({0}) from type_detail where event = '{1}' \
      group by host, time order by host, time".format(metric, event), self.conn)
      if df[event].isnull().values.any():
        del df[event]
      print("time to compute events {0}: {1}".format(event, time.time() -s))

    df = df.reset_index()
    df["time"] = df["time"].dt.tz_convert('US/Central').dt.tz_localize(None)

    plots = []
    for event,unit in event_list:
      if event not in df.columns: continue
      plots += [self.plot_metric(df, event, unit)]

    return gridplot(plots, ncols = len(plots)//4 + 1)
