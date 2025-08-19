"""Plots for displaying database data."""

from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import Row, column, row
from bokeh.models import ColumnDataSource, CustomJS, HoverTool, Range1d
from bokeh.models.widgets import Button, Div, MultiChoice
from bokeh.plotting import figure

from . import models, timeseries, widgets
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
    selected_projects: list[str] | None = None,
    selected_users: list[str] | None = None,
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
        selected_projects: (optional) list of selected project name(s)
        selected_users: (optional) list of selected user name(s)

    Returns:
        Bokeh figure layout with timeseries data plot and MultiChoice widgets.

    """
    # collect project names and users'm names
    all_projects = list(
        models.Project.objects.values_list("name", flat=True).distinct()
    )
    all_users = list(models.User.objects.values_list("username", flat=True).distinct())

    if not selected_projects:
        use_projects = all_projects
    else:
        use_projects = selected_projects

    if not selected_users:
        use_users = all_users
    else:
        use_users = selected_users

    # Total effort for selected project(s)
    total_effort_timeseries = None
    for proj in use_projects:
        project_effort_timeseries = timeseries.get_project_effort_timeseries(
            start_date, end_date, proj
        )
        if total_effort_timeseries is None:
            total_effort_timeseries = project_effort_timeseries
        else:
            total_effort_timeseries += project_effort_timeseries

    # total capacity for selected user(s)
    total_capacity_timeseries = None
    for usr in use_users:
        user_capacity_timeseries = timeseries.get_user_capacity_timeseries(
            start_date, end_date, usr
        )
        if total_capacity_timeseries is None:
            total_capacity_timeseries = user_capacity_timeseries
        else:
            total_capacity_timeseries += user_capacity_timeseries

    traces = [
        {
            "timeseries": total_capacity_timeseries,
            "colour": "navy",
            "label": "Total Capacity",
        },
        {
            "timeseries": total_effort_timeseries,
            "colour": "firebrick",
            "label": "Total effort",
        },
    ]

    plot = create_timeseries_plot(
        title="Project effort and team capacity over time",
        traces=traces,
        x_range=x_range,
    )

    plot.width = 900  # width of the plot

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

    # List for projects and users for multi-choice selection
    all_projects = list(
        models.Project.objects.values_list("name", flat=True).distinct()
    )
    all_users = list(models.User.objects.values_list("username", flat=True).distinct())

    # Get the plot to display (it is created with all data, but only the dates
    # in the x_range provided are shown) with all projects and users selected
    plot = create_capacity_planning_plot(
        start_date=min_date,
        end_date=max_date,
        x_range=(start, end),
        selected_projects=[],  # empty implies all projects selected
        selected_users=[],  # empty implies all users selected
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

    # Project(s) for selection
    project_options = all_projects
    project_title = Div(text="<h3>Select Projects</h3>", width=180)
    project_multichoice = MultiChoice(
        options=[(opt, opt) for opt in project_options],
        value=[],  # empty default implies all projects efforts selected
        width=180,  # width of the multichoice fr projects
    )

    # User(s) selection
    user_options = all_users
    user_title = Div(text="<h3>Select Users</h3>", width=180)
    user_multichoice = MultiChoice(
        options=[(opt, opt) for opt in user_options],
        value=[],  # empty default implies all users capacity selected
        width=180,  # width of the multichoice for users
    )

    # Button to clear all filters and reset plot to default state
    reset_project_button = Button(label="Reset Projects", width=100)
    reset_user_button = Button(label="Reset Users", width=100)

    # combined callback
    callback_code = CustomJS(
        args=dict(
            plot=plot,
            project_multichoice=project_multichoice,
            user_multichoice=user_multichoice,
            start_picker=start_picker,
            end_picker=end_picker,
            min_date=min_date,
            max_date=max_date,
        ),
        code="""
            console.log("Selected projects:", project_multichoice.value);
            console.log("Selected users:", user_multichoice.value);
            plot.change.emit();
        """,
    )

    project_reset_callback_code = CustomJS(
        args=dict(project_multichoice=project_multichoice),
        code="""
            project_multichoice.value = [];  // Reset to empty implying all projects
            project_multichoice.change.emit();
        """,
    )

    user_reset_callback_code = CustomJS(
        args=dict(user_multichoice=user_multichoice),
        code="""
            user_multichoice.value = [];  // Reset to empty implying all users
            user_multichoice.change.emit();
        """,
    )

    project_multichoice.js_on_change("value", callback_code)
    user_multichoice.js_on_change("value", callback_code)
    reset_project_button.js_on_click(project_reset_callback_code)
    reset_user_button.js_on_click(user_reset_callback_code)

    grouping = column(
        start_picker,
        end_picker,
        calendar_button,
        financial_button,
        project_title,
        project_multichoice,
        reset_project_button,
        user_title,
        user_multichoice,
        reset_user_button,
        width=180,
        spacing=5,
    )

    # Create layout to display widgets aligned as a column next to the plot
    plot_layout = row(grouping, plot, spacing=10)
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
