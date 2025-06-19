"""Plots for displaying database data."""

from datetime import datetime

import bokeh
import pandas as pd
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

from . import timeseries


def get_bokeh_version() -> str:
    """Get Bokeh version for HTML script tags."""
    return bokeh.__version__


def calculate_traces(start_date: datetime, end_date: datetime) -> ColumnDataSource:
    """Get data from the Django database for the capacity planning traces.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

    Returns:
        Bokeh ColumnDataSource object containing Effort and Capacity timeseries
        columns.
    """
    effort_timeseries = timeseries.get_effort_timeseries(start_date, end_date)
    capacity_timeseries = timeseries.get_capacity_timeseries(start_date, end_date)
    timeseries_df = pd.DataFrame(
        {"Effort": effort_timeseries, "Capacity": capacity_timeseries}
    )
    timeseries_df.reset_index(inplace=True)
    source = ColumnDataSource(timeseries_df)
    return source


def create_timeseries_plot(start_date: datetime, end_date: datetime) -> figure:
    """Generates all the time series data for the capacity planning plot.

    Includes all business days between the selected start and end date, inclusive of
    the start date. Time for the effort (aggregated over all projects) and
    capacity (aggregated over all users) are calculated.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

    Returns:
        Bokeh figure containing timeseries data.
    """
    source = calculate_traces(start_date, end_date)
    plot = figure(
        title="Project effort and team capacity over time",
        width=1000,
        height=500,
        background_fill_color="#efefef",
        x_axis_type="datetime",  # type: ignore[call-arg]
        tools="save,xpan,xwheel_zoom,reset",
    )
    plot.yaxis.axis_label = "Value"
    plot.xaxis.axis_label = "Date"
    plot.line(
        "index",
        "Effort",
        source=source,
        line_width=2,
        color="firebrick",
        legend_label="Project effort",
    )
    plot.line(
        "index",
        "Capacity",
        source=source,
        line_width=2,
        color="navy",
        legend_label="Capacity",
    )
    plot.legend.click_policy = "hide"  # hides traces when clicked in legend
    return plot
