"""Plots for displaying database data."""

from datetime import datetime, time
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import Row, column, row
from bokeh.models import ColumnDataSource, CustomJS, HoverTool
from bokeh.models.widgets import Button, CheckboxGroup
from bokeh.plotting import figure

from . import timeseries
from .utils import get_month_dates_for_previous_year


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


def create_capacity_planning_plot(start_date: datetime, end_date: datetime) -> Row:
    """Generates all the time series data and creates the capacity planning plot.

    Includes all business days between the selected start and end date, inclusive of
    the start date. Time for the effort (aggregated over all projects) and
    capacity (aggregated over all users) are calculated.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

    Returns:
        Tuple containing Bokeh figure with timeseries data, CheckboxGroup widget,
        and Button.

    """
    # Get effort for each project
    PROJECTS = ["proCAT 1", "proCAT 2", "proCAT 3", "proCAT 4"]
    project_colours = ["firebrick", "orange", "green", "blue"]

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

    plot = create_timeseries_plot(
        title="Project effort and team capacity over time", traces=traces
    )

    plot.yaxis.axis_label = "Effort (hours)"

    plot.width = 800  # Reduce the width to fit the checkbox section

    checkbox_labels = ["Capacity", "Total effort", *PROJECTS]

    checkbox_group = CheckboxGroup(
        labels=checkbox_labels,
        active=[0, 1],  # Default to show capacity and total effort only
        width=200,  # width of the checkbox group
    )

    # Button to clear all filters and reset plot to default state
    reset_button = Button(label="Clear filters", width=100)

    callback_code = CustomJS(
        args=dict(plot=plot),
        code="""
            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');

            // Hide all lines
            line_renderers.forEach(r => {r.visible = false});

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

    reset_callback_code = CustomJS(
        args=dict(plot=plot, checkbox_group=checkbox_group),
        code="""
            // Reset all checkboxes to default state
            checkbox_group.active = [0, 1]; // Show only capacity and total effort

            // Get all line renderers from the plot
            const line_renderers = plot.renderers.filter(r => r.glyph &&
            r.glyph.type === 'Line');

            // Hide all lines
            line_renderers.forEach(r => {r.visible = false});

            // Show only the default lines (capacity and total effort)
            [0, 1].forEach(index => {
                if (index < line_renderers.length) {
                    line_renderers[index].visible = true;
                }
            });

            // Plot update
            checkbox_group.change.emit();
            plot.change.emit();
        """,
    )
    checkbox_group.js_on_change("active", callback_code)
    reset_button.js_on_click(reset_callback_code)

    grouping = column(checkbox_group, reset_button, width=200)

    layout = row(plot, grouping)

    return layout


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


def html_components_from_plot(plot: Row, prefix: str | None = None) -> dict[str, str]:
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
