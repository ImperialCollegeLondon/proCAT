"""Plots for displaying database data."""

from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import Row, column, row
from bokeh.models import ColumnDataSource, CustomJS, HoverTool, Range1d
from bokeh.models.widgets import Button, Div, MultiChoice
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
        Bokeh Row layout with timeseries data plot and CheckboxGroup widgets.

    """
    # Get effort for each project and user
    PROJECTS = ["proCAT 1", "proCAT 2", "proCAT 3", "proCAT 4"]
    USERS = ["User 1", "User 2", "User 3", "User 4", "User 5"]
    project_colours = ["firebrick", "orange", "green", "blue"]
    user_colours = ["purple", "brown", "pink", "cyan", "magenta"]

    # Total effort and capacity across all projects
    total_effort_timeseries = timeseries.get_effort_timeseries(start_date, end_date)
    capacity_timeseries = timeseries.get_capacity_timeseries(start_date, end_date)

    traces = [
        {"timeseries": capacity_timeseries, "colour": "navy", "label": "Capacity"},
        {
            "timeseries": total_effort_timeseries,
            "colour": "black",
            "label": "Total effort",
        },
    ]

    # Add effort for each project
    for i, project in enumerate(PROJECTS):
        project_effort_timeseries = timeseries.get_project_effort_timeseries(
            start_date, end_date, project
        )
        traces.append(
            {
                "timeseries": project_effort_timeseries,
                "colour": project_colours[i],
                "label": project,
            }
        )

    # Add effort for each user
    for i, user in enumerate(USERS):
        user_effort_timeseries = timeseries.get_user_effort_timeseries(
            start_date, end_date, user
        )
        traces.append(
            {
                "timeseries": user_effort_timeseries,
                "colour": user_colours[i],
                "label": user,
            }
        )

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

    # List for projects and users for multi-choice selection
    PROJECTS = ["proCAT 1", "proCAT 2", "proCAT 3", "proCAT 4"]
    USERS = ["User 1", "User 2", "User 3", "User 4", "User 5"]

    # Project(s) for selection
    project_options = ["Capacity", "Total effort", *PROJECTS]
    project_title = Div(text="<h3>Projects</h3>", width=180)
    project_multichoice = MultiChoice(
        options=[(opt, opt) for opt in project_options],
        value=[
            "Capacity",
            "Total effort",
        ],  # Default to show capacity and total effort only
        width=180,  # width of the multichoice fr projects
    )

    # User(s) selection
    user_options = ["Capacity", "Total effort", *USERS]
    user_title = Div(text="<h3>Users</h3>", width=180)
    user_multichoice = MultiChoice(
        options=[(opt, opt) for opt in user_options],
        value=[
            "Capacity",
            "Total effort",
        ],  # Default to show capacity and total effort only
        width=180,  # width of the multichoice for users
    )

    # Button to clear all filters and reset plot to default state
    reset_project_button = Button(label="Reset Projects", width=100)
    reset_user_button = Button(label="Reset Users", width=100)

    # Project callback
    project_callback_code = CustomJS(
        args=dict(plot=plot),
        code="""
            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');

            // Projects traces are from 0 to projects_labels.length - 1
            const project_count = cb_obj.labels.length;

            // Hide all lines
            for (let i = 0; i < project_count && i < line_renderers.length; i++) {
                line_renderers[i].visible = false;
            }

            // Check if any projects are selected
            // Skip first two indices (Capacity and Total effort)
            const project_indices = cb_obj.active.filter(index => index >= 2);
            const has_projects_selected = project_indices.length > 0;

            if (has_projects_selected) {
                // Show only the selected projects
                project_indices.forEach(index => {
                    if (index < line_renderers.length) {
                        line_renderers[index].visible = true;
                    }
                });
            } else {
                // If no projects are selected, show only Capacity and Total effort
                cb_obj.active.forEach(index => {
                    if (index < 2 && index < line_renderers.length) {
                        line_renderers[index].visible = true;
                    }
                });
            }

            // Plot update
            plot.change.emit();
        """,
    )

    # User callback
    user_callback_code = CustomJS(
        args=dict(plot=plot),
        code="""
            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');

            // User start index
            const project_count = project_multichoice.labels.length;
            const user_start_index = project_count;

            // Hide all lines
            for (let i = user_start_index; i < line_renderers.length; i++) {
                line_renderers[i].visible = false;
            }

            // show selected users
            cb_obj.active.forEach(user_index => {
                const actual_index = user_index + user_start_index;
                if (actual_index < line_renderers.length) {
                    line_renderers[actual_index].visible = true;
                }
            });

            // Plot update
            plot.change.emit();
        """,
    )

    project_reset_callback_code = CustomJS(
        args=dict(project_multichoice=project_multichoice, plot=plot),
        code="""
            // Reset all checkboxes to default state
            project_multichoice.active = [0, 1]; // Show only capacity and total effort

            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');

            // Hide all lines
            for (let i = 0; i < project_count && i < line_renderers.length; i++) {
                line_renderers[i].visible = false;
            }

            // Show only the default lines (capacity and total effort)
            [0, 1].forEach(index => {
                if (index < line_renderers.length) {
                    line_renderers[index].visible = true;
                }
            });

            // Plot update
            project_multichoice.change.emit();
            plot.change.emit();
        """,
    )

    user_reset_callback_code = CustomJS(
        args=dict(user_multichoice=user_multichoice, plot=plot),
        code="""
            // Reset all checkboxes to default state
            user_multichoice.active = [0, 1]; // Show only capacity and total effort

            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');
            const project_count = project_multichoice.labels.length;

            // Hide all lines
            for (let i = project_count; i < line_renderers.length; i++) {
                line_renderers[i].visible = false;
            }

            // Plot update
            user_multichoice.change.emit();
            plot.change.emit();
        """,
    )

    project_multichoice.js_on_change("value", project_callback_code)
    user_multichoice.js_on_change("value", user_callback_code)
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
