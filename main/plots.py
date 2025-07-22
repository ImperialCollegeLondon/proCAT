"""Plots for displaying database data."""

from datetime import datetime, time
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure

from . import timeseries
from .utils import get_month_dates_for_previous_year


def create_bar_plot(title: str, dates: list[str], values: list[float]) -> figure:
    """Creates a bar plot with dates versus values.

    Args:
        title: plot title
        dates: a list of dates to display on the x-axis
        values: a list of values for the bars

    Returns:
        Bokeh figure for the bar chart.
    """
    source = ColumnDataSource(data=dict(dates=dates, values=values))
    plot = figure(
        x_range=dates,  # type: ignore[arg-type]
        title=title,
        width=1000,
        height=500,
        background_fill_color="#efefef",
    )
    plot.yaxis.axis_label = "Total charge (£)"
    plot.xaxis.axis_label = "Date"
    plot.vbar(x="dates", top="values", width=0.5, source=source)

    # Add basic tooltips to show monthly totals
    hover = HoverTool()
    hover.tooltips = [
        ("Month", "@dates"),
        ("Total", "£@values"),
    ]
    plot.add_tools(hover)
    return plot


def create_timeseries_plot(  # type: ignore[explicit-any]
    title: str,
    traces: list[dict[str, Any]],
) -> figure:
    """Creates a generic timeseries plot.

    Args:
        title: plot title
        traces: a list of dictionaries with keys for the 'timeseries' data, 'label' and
            'colour'

    Returns:
        Bokeh figure containing timeseries data.
    """
    # Create ColumnDataSource from trace data
    df = pd.DataFrame({trace["label"]: trace["timeseries"] for trace in traces})
    df.reset_index(inplace=True)
    source = ColumnDataSource(df)

    plot = figure(
        title=title,
        width=1000,
        height=500,
        background_fill_color="#efefef",
        x_axis_type="datetime",  # type: ignore[call-arg]
        tools="save,xpan,xwheel_zoom,reset",
    )
    plot.yaxis.axis_label = "Value"
    plot.xaxis.axis_label = "Date"
    for trace in traces:
        plot.line(
            "index",
            trace["label"],
            source=source,
            line_width=2,
            color=trace["colour"],
            legend_label=trace["label"],
        )
    plot.legend.click_policy = "hide"  # hides traces when clicked in legend
    return plot


def create_capacity_planning_plot(start_date: datetime, end_date: datetime) -> figure:
    """Generates all the time series data and creates the capacity planning plot.

    Includes all business days between the selected start and end date, inclusive of
    the start date. Time for the effort (aggregated over all projects) and
    capacity (aggregated over all users) are calculated.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

    Returns:
        Bokeh figure containing timeseries data.
    """
    effort_timeseries = timeseries.get_effort_timeseries(start_date, end_date)
    capacity_timeseries = timeseries.get_capacity_timeseries(start_date, end_date)
    traces = [
        {
            "timeseries": effort_timeseries,
            "colour": "firebrick",
            "label": "Project effort",
        },
        {"timeseries": capacity_timeseries, "colour": "navy", "label": "Capacity"},
    ]
    plot = create_timeseries_plot(
        title="Project effort and team capacity over time", traces=traces
    )
    return plot


def create_cost_recovery_plots() -> tuple[figure, figure]:
    """Creates the cost recovery plot for the last year.

    Provides an overview of team capacity over the past year and the project charging.

    Returns:
        Tuple of Bokeh figures containing cost recovery data timeseries data and
            monthly charges for the past year.
    """
    dates = get_month_dates_for_previous_year()

    # Get start and end date as datetimes for capacity timeseries
    start_date = datetime.combine(dates[0][0], time.min)
    end_date = datetime.combine(dates[-1][1], time.min)

    # Create timeseries plot
    cost_recovery_timeseries, monthly_totals = timeseries.get_cost_recovery_timeseries(
        dates
    )
    capacity_timeseries = timeseries.get_capacity_timeseries(
        start_date=start_date, end_date=end_date
    )
    traces = [
        {
            "timeseries": cost_recovery_timeseries,
            "colour": "gold",
            "label": "Capacity used",
        },
        {"timeseries": capacity_timeseries, "colour": "navy", "label": "Capacity"},
    ]
    timeseries_plot = create_timeseries_plot(
        title="Team capacity and project charging for the past year", traces=traces
    )

    # Create bar plot for monthly charges
    chart_dates = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]
    bar_plot = create_bar_plot(
        title="Monthly charges for the past year",
        dates=chart_dates,
        values=monthly_totals,
    )

    return timeseries_plot, bar_plot


def html_components_from_plot(
    plot: figure, prefix: str | None = None
) -> dict[str, str]:
    """Generate HTML components from a Bokeh plot that can be added to the context.

    Args:
        plot: Bokeh figure to be added to the context
        prefix: optional prefix to use in the context keys
    """
    script, div = components(plot)
    if prefix:
        return {
            f"{prefix}_script": script,
            f"{prefix}_div": div,
        }

    else:
        return {
            "script": script,
            "div": div,
        }
