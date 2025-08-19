"""Plots for displaying database data."""

from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, HoverTool, Range1d
from bokeh.models.layouts import Row
from bokeh.models.widgets import Button
from bokeh.plotting import figure

from . import timeseries, widgets
from .utils import (
    get_calendar_year_dates,
    get_financial_year_dates,
    get_month_dates_for_previous_year,
)


def create_bar_plot(title: str, months: list[str], values: list[float]) -> figure:
    """Creates a bar plot with dates versus values.

    Args:
        title: plot title
        months: a list of months to display on the x-axis
        values: a list of total charge values for the bar height indicate on the y-axis

    Returns:
        Bokeh figure for the bar chart.
    """
    source = ColumnDataSource(data=dict(months=months, values=values))
    plot = figure(
        x_range=months,  # type: ignore[arg-type]
        title=title,
        width=1000,
        height=500,
        background_fill_color="#efefef",
    )
    plot.yaxis.axis_label = "Total charge (£)"
    plot.xaxis.axis_label = "Month-Year"
    plot.vbar(x="months", top="values", width=0.5, source=source)

    # Add basic tooltips to show monthly totals
    hover = HoverTool()
    hover.tooltips = [
        ("Month", "@months"),
        ("Total", "£@values"),
    ]
    plot.add_tools(hover)
    return plot


def create_timeseries_plot(  # type: ignore[explicit-any]
    title: str,
    traces: list[dict[str, Any]],
    x_range: tuple[datetime, datetime] | None = None,
) -> figure:
    """Creates a generic timeseries plot.

    Args:
        title: plot title
        traces: a list of dictionaries with keys for the 'timeseries' data, 'label' and
            'colour'
        x_range: (optional) tuple of datetimes to use as the x_range for the displayed
            plot

    Returns:
        Bokeh figure containing timeseries data.
    """
    # Create ColumnDataSource from trace data
    df = pd.DataFrame({trace["label"]: trace["timeseries"] for trace in traces})
    df.reset_index(inplace=True)
    df["index"] = pd.to_datetime(df["index"]).dt.date
    source = ColumnDataSource(df)

    plot = figure(
        title=title,
        width=1000,
        height=500,
        background_fill_color="#efefef",
        x_axis_type="datetime",  # type: ignore[call-arg]
        tools="save,xpan,xwheel_zoom,reset",
    )
    if x_range:
        plot.x_range = Range1d(x_range[0], x_range[1])
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


def create_capacity_planning_plot(
    start_date: datetime,
    end_date: datetime,
    x_range: tuple[datetime, datetime] | None = None,
) -> figure:
    """Generates all the time series data and creates the capacity planning plot.

    Includes all business days between the selected start and end date, inclusive of
    the start date. Time for the effort (aggregated over all projects) and
    capacity (aggregated over all users) are calculated.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period
        x_range: (optional) tuple of datetimes to use as the x_range for the displayed
            plot

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
        title="Project effort and team capacity over time",
        traces=traces,
        x_range=x_range,
    )
    return plot


def create_capacity_planning_layout() -> Row:
    """Create the capacity planning plot in layout with widgets.

    Creates the capacity planning plot plus the associated widgets used to control the
    data displayed in the plot.

    Returns:
        A Row object (the Row containing a Column of widgets and the plot).
    """
    start, end = datetime.now(), datetime.now() + timedelta(days=365)
    # Min and max dates are three years before and ahead of current date
    min_date, max_date = start - timedelta(days=1095), start + timedelta(days=1095)

    # Get the plot to display (it is created with all data, but only the dates
    # in the x_range provided are shown)
    plot = create_capacity_planning_plot(
        start_date=min_date, end_date=max_date, x_range=(start, end)
    )

    # Create date picker widgets to control the dates shown in the plot
    start_picker, end_picker = widgets.get_plot_date_pickers(
        min_date=min_date.date(),
        max_date=max_date.date(),
        default_start=start.date(),
        default_end=end.date(),
    )
    widgets.add_timeseries_callback_to_date_pickers(start_picker, end_picker, plot)

    # Create buttons to set plot dates to some defaults
    calendar_button = Button(
        label="Current calendar year",
    )
    widgets.add_callback_to_button(
        button=calendar_button,
        dates=get_calendar_year_dates(),
        plot=plot,
        start_picker=start_picker,
        end_picker=end_picker,
    )

    financial_button = Button(
        label="Current financial year",
    )
    widgets.add_callback_to_button(
        button=financial_button,
        dates=get_financial_year_dates(),
        plot=plot,
        start_picker=start_picker,
        end_picker=end_picker,
    )

    # Create layout to display widgets aligned as a column next to the plot
    plot_layout = row(
        column(start_picker, end_picker, calendar_button, financial_button), plot
    )
    return plot_layout


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
        title=(
            f"Team capacity and project charging from {start_date.strftime('%B')} "
            f"{start_date.year} to {end_date.strftime('%B')} {end_date.year}"
        ),
        traces=traces,
    )

    # Create bar plot for monthly charges
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]
    bar_plot = create_bar_plot(
        title=(
            f"Monthly charges from {start_date.strftime('%B')} {start_date.year} to "
            f"{end_date.strftime('%B')} {end_date.year}"
        ),
        months=chart_months,
        values=monthly_totals,
    )

    return timeseries_plot, bar_plot


def html_components_from_plot(
    plot: figure | Row, prefix: str | None = None
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

    return {
        "script": script,
        "div": div,
    }
