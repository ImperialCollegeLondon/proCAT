"""Plots for displaying database data."""

from datetime import datetime, time

import pandas as pd
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure

from . import timeseries
from .utils import get_month_dates_for_previous_year


def calculate_capacity_planning_traces(
    start_date: datetime, end_date: datetime
) -> ColumnDataSource:
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


def calculate_cost_recovery_traces() -> tuple[ColumnDataSource, ColumnDataSource]:
    """Get data from the Django database for the capacity and cost recovery traces.

    Returns:
        Tuple of ColumnDataSources for the Cost Recovery timeseries and total monthly
            charges data.
    """
    dates = get_month_dates_for_previous_year()

    # Get start and end date as datetimes for capacity timeseries
    start_date = datetime.combine(dates[0][0], time.min)
    end_date = datetime.combine(dates[-1][1], time.min)
    capacity_timeseries = timeseries.get_capacity_timeseries(
        start_date=start_date, end_date=end_date
    )

    cost_recovery_timeseries, monthly_totals = timeseries.get_cost_recovery_timeseries(
        dates
    )

    timeseries_df = pd.DataFrame(
        {"Capacity": capacity_timeseries, "Cost recovery": cost_recovery_timeseries}
    )
    timeseries_df.reset_index(inplace=True)
    timeseries_source = ColumnDataSource(timeseries_df)

    # Create bar plot data source
    chart_dates = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]
    bar_source = ColumnDataSource(data=dict(dates=chart_dates, values=monthly_totals))

    return timeseries_source, bar_source


def create_bar_plot(source: ColumnDataSource, title: str) -> figure:
    """Creates a bar plot.

    Args:
        source: Bokeh ColumnDataSource object containing data.
        title: plot title

    Returns:
        Bokeh figure for the bar chart.
    """
    plot = figure(
        x_range=list(source.data["dates"]),
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
        ("Total", "@values"),
    ]
    plot.add_tools(hover)
    return plot


def create_timeseries_plot(
    source: ColumnDataSource,
    title: str,
    traces: list[dict[str, str]],
) -> figure:
    """Creates a generic timeseries plot.

    Args:
        source: Bokeh ColumnDataSource object containing the timeseries columns.
        title: plot title
        traces: a list of dictionaries with keys for the 'col_name', 'colour', and
            'legend_label' for each trace

    Returns:
        Bokeh figure containing timeseries data.
    """
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
            trace["col_name"],
            source=source,
            line_width=2,
            color=trace["colour"],
            legend_label=trace["legend_label"],
        )
    plot.legend.click_policy = "hide"  # hides traces when clicked in legend
    return plot


def create_capacity_planning_plot(start_date: datetime, end_date: datetime) -> figure:
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
    source = calculate_capacity_planning_traces(start_date, end_date)

    # provide info needed to plot as dictionary for each trace
    traces = [
        {"col_name": "Effort", "colour": "firebrick", "legend_label": "Project effort"},
        {"col_name": "Capacity", "colour": "navy", "legend_label": "Capacity"},
    ]
    plot = create_timeseries_plot(
        source=source, title="Project effort and team capacity over time", traces=traces
    )

    return plot


def create_cost_recovery_plots() -> tuple[figure, figure]:
    """Creates the cost recovery plot for the last year.

    Provides an overview of team capacity over the past year and the project charging.

    Returns:
        Tuple of Bokeh figures containing cost recovery data timeseries data and
            monthly charges for the past year.
    """
    timeseries_source, bar_source = calculate_cost_recovery_traces()

    # provide info needed to plot as dictionary for each trace
    traces = [
        {
            "col_name": "Cost recovery",
            "colour": "gold",
            "legend_label": "Capacity used",
        },
        {"col_name": "Capacity", "colour": "navy", "legend_label": "Capacity"},
    ]
    timeseries_plot = create_timeseries_plot(
        source=timeseries_source,
        title="Team capacity and project charging for the past year",
        traces=traces,
    )

    bar_plot = create_bar_plot(bar_source, "Monthly charges for the past year")

    return timeseries_plot, bar_plot
