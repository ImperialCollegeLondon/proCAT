"""Plots for displaying database data."""

from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import Row, column, row
from bokeh.models import ColumnDataSource, HoverTool, Range1d
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
    use_projects: list[str] | None = None,
    use_users: list[str] | None = None,
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
        use_projects: (optional) list of project name(s) to use in the plot
        use_users: (optional) list of user name(s) to use in the plot

    Returns:
        Bokeh figure layout with timeseries data plot and MultiChoice widgets.

    """
    # dates for the whole time range
    dates = pd.date_range(start=start_date, end=end_date, inclusive="left")

    # collect all projects and users
    all_projects = list(
        models.Project.objects.values_list("name", flat=True).distinct()
    )
    all_users = list(models.User.objects.values_list("username", flat=True).distinct())

    # a data dictionary
    data_dict: dict[str, object] = {
        "index": dates,
    }

    # include individual project effort and calculate total effort
    total_effort_timeseries = pd.Series(0.0, index=dates, name="Total Effort")
    for proj in all_projects:
        try:
            project_effort_timeseries = timeseries.get_project_effort_timeseries(
                start_date, end_date, proj
            )
            project_effort_timeseries = project_effort_timeseries.reindex(
                dates, fill_value=0.0
            )

            # add as column for JS aggregation
            data_dict[f"effort_{proj}"] = project_effort_timeseries.values

            # add to total if proj is in use_projects or all if use_projects is None
            if not use_projects or proj in use_projects:
                total_effort_timeseries += project_effort_timeseries
        except Exception:
            # when proj has no data
            data_dict[f"effort_{proj}"] = [0.0] * len(dates)

    # include individual user capacity and calculate total capacity
    total_capacity_timeseries = pd.Series(0.0, index=dates, name="Total Capacity")
    for usr in all_users:
        try:
            user_capacity_timeseries = timeseries.get_user_capacity_timeseries(
                start_date, end_date, usr
            )
            user_capacity_timeseries = user_capacity_timeseries.reindex(
                dates, fill_value=0.0
            )

            # add as column for JS aggregation
            data_dict[f"capacity_{usr}"] = user_capacity_timeseries.values

            # add to total if this usr is in use_users or all if use_users is None
            if not use_users or usr in use_users:
                total_capacity_timeseries += user_capacity_timeseries
        except Exception:
            # when usr has no data
            data_dict[f"capacity_{usr}"] = [0.0] * len(dates)

    # add aggregated totals
    data_dict["Total effort"] = total_effort_timeseries.values
    data_dict["Total Capacity"] = total_capacity_timeseries.values

    # create a ColumnDataSource with all data in the data dictionary
    source = ColumnDataSource(data=data_dict)

    # create plot
    plot = figure(
        title="Project effort and team capacity over time",
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

    # plot aggregated traces
    plot.line(
        "index",
        "Total Capacity",
        source=source,
        line_width=2,
        color="navy",
        legend_label="Total Capacity",
    )

    plot.line(
        "index",
        "Total effort",
        source=source,
        line_width=2,
        color="firebrick",
        legend_label="Total Effort",
    )

    plot.legend.click_policy = "hide"  # hides traces when clicked in legend

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
        use_projects=[],  # empty implies all projects selected
        use_users=[],  # empty implies all users selected
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
    widgets.get_combined_callback(
        plot=plot,
        project_multichoice=project_multichoice,
        user_multichoice=user_multichoice,
        start_picker=start_picker,
        end_picker=end_picker,
        min_date=min_date.date(),
        max_date=max_date.date(),
    )

    # Reset callbacks
    reset_project_callback = widgets.get_reset_project_callback(
        project_multichoice=project_multichoice,
        user_multichoice=user_multichoice,
        plot=plot,
    )
    reset_project_button.js_on_click(reset_project_callback)

    reset_user_callback = widgets.get_reset_user_callback(
        project_multichoice=project_multichoice,
        user_multichoice=user_multichoice,
        plot=plot,
    )
    reset_user_button.js_on_click(reset_user_callback)

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
