"""Plots for displaying database data."""

from datetime import date, datetime, time, timedelta
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, HoverTool, Range1d, VArea
from bokeh.models.layouts import Row
from bokeh.models.widgets import Button
from bokeh.plotting import figure

from . import timeseries, widgets
from .utils import (
    get_calendar_year_dates,
    get_financial_year_dates,
    get_month_dates_for_previous_years,
)


def add_varea_glyph(
    plot: figure, df: pd.DataFrame, upper_trace: str, lower_trace: str, colour: str
) -> None:
    """Adds a varea glyph to add shading between traces.

    The shading is applied when the upper trace is above the lower trace. If below,
    no shading is applied. VArea creates this shading between two sets of y-values:
    the element-wise maximum of the two traces and the lower trace. Otherwise, the
    shading is applied whenever either trace is above the other.

    Args:
        plot: the plot to add the glyph to
        df: pandas DataFrame containing trace data
        upper_trace: the label of the upper trace
        lower_trace: the label of the lower trace
        colour: the colour to apply to the shading
    """
    source = ColumnDataSource(
        {
            "index": df["index"],
            "y1": df[lower_trace],
            "y2": df[upper_trace].combine(df[lower_trace], max),
        }
    )
    plot.add_glyph(
        source, VArea(x="index", y1="y1", y2="y2", fill_color=colour, fill_alpha=0.3)
    )


def create_bar_plot(
    title: str,
    months: list[str],
    values: list[float],
    x_range: list[str] | None = None,
) -> figure:
    """Creates a bar plot with dates versus values.

    Args:
        title: plot title
        months: a list of months to display on the x-axis
        values: a list of total charge values for the bar height indicate on the y-axis
        x_range: (optional) list of values to use as the x_range for the displayed plot

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
    if x_range:
        plot.x_range.factors = x_range  # type: ignore[attr-defined]
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
    vareas: tuple[tuple[tuple[str, str], str], ...] | None = None,
) -> figure:
    """Creates a generic timeseries plot.

    Args:
        title: plot title
        traces: a list of dictionaries with keys for the 'timeseries' data, 'label' and
            'colour'
        x_range: (optional) tuple of datetimes to use as the x_range for the displayed
            plot
        vareas: (optional) tuple of tuples, containing a tuple of trace labels to apply
            shading between and the colour to use, e.g.
            ((("Capacity", "Project effort"), "Green"), ...)

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

    # If provided, add varea shading between traces
    if vareas:
        for labels, colour in vareas:
            add_varea_glyph(plot, df, labels[0], labels[1], colour)

    hover = HoverTool(
        tooltips=[
            ("Date", "$x{%F}"),
            ("Value", "$y{0.00}"),
        ],
        formatters={"$x": "datetime"},
    )
    plot.add_tools(hover)

    plot.legend.click_policy = "hide"  # hides traces when clicked in legend

    return plot


def create_capacity_planning_plot(
    start_date: datetime,
    end_date: datetime,
    x_range: tuple[datetime, datetime] | None = None,
) -> figure:
    """Generates all the time series data and creates the capacity planning plot.

    Includes all business days between the selected start and end date, inclusive of
    the start date. Timeseries for the effort (separate traces depending on project
    status) and capacity (aggregated over all users) are calculated.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period
        x_range: (optional) tuple of datetimes to use as the x_range for the displayed
            plot

    Returns:
        Bokeh figure containing timeseries data.
    """
    # Create overall capacity timeseries
    capacity_timeseries = timeseries.get_capacity_timeseries(start_date, end_date)
    traces = [
        {"timeseries": capacity_timeseries, "colour": "darkgreen", "label": "Capacity"}
    ]

    # Create individual effort timeseries according to project status
    projects = (  # Traces are cumulative
        ("Tentative", "firebrick", ["Tentative", "Confirmed", "Active"]),
        ("Confirmed", "orange", ["Confirmed", "Active"]),
        ("Active", "navy", ["Active"]),
    )
    for status, colour, filter in projects:
        effort_timeseries = timeseries.get_effort_timeseries(
            start_date, end_date, filter
        )
        traces.append(
            {
                "timeseries": effort_timeseries,
                "colour": colour,
                "label": f"{status} project effort",
            },
        )

    # Apply area shading between select traces
    vareas = (
        (("Capacity", "Confirmed project effort"), "green"),
        (("Confirmed project effort", "Active project effort"), "yellow"),
        (("Tentative project effort", "Confirmed project effort"), "red"),
    )

    plot = create_timeseries_plot(
        title="Project effort and team capacity over time",
        traces=traces,
        x_range=x_range,
        vareas=vareas,
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


def create_cost_recovery_plots(
    dates: list[tuple[date, date]],
    start_date: datetime,
    end_date: datetime,
    x_range: tuple[datetime, datetime],
    chart_months: list[str],
) -> tuple[figure, figure]:
    """Creates the cost recovery plot for the last year.

    Provides an overview of team capacity over the past year and the project charging.

    Args:
        dates: list of tuples (from oldest to most recent) containing dates for all
            months of the last 3 years; each tuple contains two dates for the first
            and last date of the month
        start_date: datetime object representing the start of the timeseries plotting
            period
        end_date: datetime object representing the end of the timeseries plotting
            period
        x_range: (optional) tuple of datetimes to use as the x_range for the displayed
            plot
        chart_months: list of months for x-axis in bar chart

    Returns:
        Tuple of Bokeh figures containing cost recovery data timeseries data and
            monthly charges for the past year.
    """
    # Create timeseries plot
    cost_recovery_timeseries, monthly_totals = timeseries.get_cost_recovery_timeseries(
        dates
    )
    capacity_timeseries = timeseries.get_capacity_timeseries(
        start_date=start_date, end_date=end_date
    )

    internal_effort_timeseries = timeseries.get_internal_effort_timeseries(
        start_date=start_date, end_date=end_date
    )

    number_team_members = timeseries.get_team_members_timeseries(
        start_date=start_date, end_date=end_date
    )

    internal_project_effort = internal_effort_timeseries / number_team_members

    # charged project effort using cost recovery timeseries divided by team members
    charged_project_effort = cost_recovery_timeseries / number_team_members

    # total project effort for all projects
    total_project_effort = charged_project_effort + internal_project_effort

    # in %
    avg_project_capacity_pct = capacity_timeseries / number_team_members * 100

    total_capacity_used_pct = total_project_effort * 100

    charged_capacity_used_pct = charged_project_effort * 100

    traces = [
        {
            "timeseries": avg_project_capacity_pct,
            "colour": "gold",
            "label": "Average capacity for project work %",
        },
        {
            "timeseries": total_capacity_used_pct,
            "colour": "navy",
            "label": "Fraction of capacity used for all projects %",
        },
        {
            "timeseries": charged_capacity_used_pct,
            "colour": "green",
            "label": "Fraction of capacity used for charged projects %",
        },
    ]
    timeseries_plot = create_timeseries_plot(
        title=("Team capacity and project charging over time"),
        traces=traces,
        x_range=x_range,
    )

    # Create bar plot for monthly charges
    bar_plot = create_bar_plot(
        title=("Total monthly charges"),
        months=chart_months,
        values=monthly_totals,
        x_range=(chart_months[-12:]),
    )
    return timeseries_plot, bar_plot


def create_cost_recovery_layout() -> Row:
    """Create the cost recovery plots in layout with widgets.

    Creates the cost recovery timeseries plot and bar plot for monthly charges, plus the
    associated widgets used to control the data displayed in the plots.

    Returns:
        A Row object (the Row containing a Column of widgets and a Column of plots).
    """
    dates = get_month_dates_for_previous_years()

    # Get start and end date as datetimes for capacity timeseries
    min_date = datetime.combine(dates[0][0], time.min)
    max_date = datetime.combine(dates[-1][1], time.min)
    start = datetime.combine(dates[-12][0], time.min)

    # Get x-axis values for bar plot
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]

    # Plots are initialised with data for last 3 years but only the last year is shown
    # by default
    timeseries_plot, bar_plot = create_cost_recovery_plots(
        dates=dates,
        start_date=min_date,
        end_date=max_date,
        x_range=(start, max_date),
        chart_months=chart_months,
    )

    # Create date picker widgets to control the dates shown in the plot
    start_picker, end_picker = widgets.get_plot_date_pickers(
        min_date=min_date.date(),
        max_date=max_date.date(),
        default_start=start.date(),
        default_end=max_date.date(),
    )
    widgets.add_timeseries_callback_to_date_pickers(
        start_picker=start_picker, end_picker=end_picker, plot=timeseries_plot
    )
    widgets.add_bar_callback_to_date_pickers(
        start_picker=start_picker,
        end_picker=end_picker,
        plot=bar_plot,
        chart_months=chart_months,
    )

    # Create button to set plots to calendar year
    calendar_button = Button(
        label="Current calendar year",
    )
    widgets.add_callback_to_button(
        button=calendar_button,
        dates=get_calendar_year_dates(),
        plot=timeseries_plot,
        start_picker=start_picker,
        end_picker=end_picker,
        include_future_dates=False,
    )
    widgets.add_bar_callback_to_button(
        button=calendar_button,
        dates=get_calendar_year_dates(),
        plot=bar_plot,
        chart_months=chart_months,
    )

    # Create button to set plots to financial year
    financial_button = Button(
        label="Current financial year",
    )
    widgets.add_callback_to_button(
        button=financial_button,
        dates=get_financial_year_dates(),
        plot=timeseries_plot,
        start_picker=start_picker,
        end_picker=end_picker,
        include_future_dates=False,
    )
    widgets.add_bar_callback_to_button(
        button=financial_button,
        dates=get_financial_year_dates(),
        plot=bar_plot,
        chart_months=chart_months,
    )

    # Create layout to display widgets aligned as a column next to the plot
    plot_layout = row(
        column(start_picker, end_picker, calendar_button, financial_button),
        column(timeseries_plot, bar_plot),
    )
    return plot_layout


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
