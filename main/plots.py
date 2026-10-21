"""Plots for displaying database data."""

from datetime import date, datetime, time, timedelta
from itertools import cycle
from math import pi
from typing import Any

import pandas as pd
from bokeh.embed import components
from bokeh.layouts import column, gridplot, row
from bokeh.models import (  # type: ignore
    ColumnDataSource,
    CrosshairTool,
    HoverTool,
    Range1d,
    Span,
    VArea,
)
from bokeh.models.layouts import Row
from bokeh.models.widgets import Button
from bokeh.palettes import Category20c
from bokeh.plotting import figure
from bokeh.transform import cumsum
from django.utils import timezone

from . import analytics, models, timeseries, widgets
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
        height=500,
        background_fill_color="#efefef",
        sizing_mode="stretch_width",
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
    height: int = 500,
    legend_loc: str = "bottom_left",
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
        height: Height of the plot in pixels. Defaults to 500.
        legend_loc: (optional) Location of the legend within the plot. Check Bokeh docs
            for valid options. Defaults to 'bottom_left'

    Returns:
        Bokeh figure containing timeseries data.
    """
    # Create ColumnDataSource from trace data
    df = pd.DataFrame({trace["label"]: trace["timeseries"] for trace in traces})
    df.index.name = "index"
    df.reset_index(inplace=True)
    df["index"] = pd.to_datetime(df["index"]).dt.date
    source = ColumnDataSource(df)

    plot = figure(
        title=title,
        height=height,
        background_fill_color="#efefef",
        x_axis_type="datetime",  # type: ignore[call-arg]
        tools="save,xpan,xwheel_zoom,reset",
        sizing_mode="stretch_width",
    )
    if x_range:
        plot.x_range = Range1d(x_range[0], x_range[1])  # type: ignore[arg-type]

    plot.yaxis.axis_label = "Value"
    plot.xaxis.axis_label = "Date"

    # Now we add the data
    lines = []
    tooltips = [
        ("Date", "@{index}{%F}"),
    ]
    hover_renderer = []
    for trace in traces:
        label = trace["label"]

        # If there's no label, that's the mark of a ghost trace used for area filling
        # and hover tooltips only. Should not appear in the legend
        if not label:
            hover_renderer = [plot.line("index", label, source=source, alpha=0)]
            continue

        # The other traces are plotted and included in the legend
        lines.append(
            plot.line(
                "index",
                label,
                source=source,
                line_width=2,
                color=trace["colour"],
                legend_label=label,
            )
        )
        tooltips.append((label, f"@{{{label}}}{{0.00}}"))

    # If provided, add varea shading between traces
    if vareas:
        for labels, colour in vareas:
            add_varea_glyph(plot, df, labels[0], labels[1], colour)

    # The tooltip appears in the hover rendered ghost trace, if any, or the first trace
    # otherwise
    hover = HoverTool(
        tooltips=tooltips,
        formatters={"@{index}": "datetime"},
        renderers=hover_renderer or lines[:1],  # type: ignore[arg-type]
        mode="vline",
    )

    plot.add_tools(hover)
    plot.legend.click_policy = "hide"  # hides traces when clicked in legend
    plot.legend.location = legend_loc  # type: ignore[assignment]

    return plot


def create_capacity_planning_plot(
    start_date: datetime,
    end_date: datetime,
    x_range: tuple[datetime, datetime] | None = None,
) -> tuple[figure, list[figure]]:
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
    capacities = timeseries.get_capacity_timeseries(start_date, end_date)
    aggregated_capacity = capacities.sum(axis=1)
    traces = [
        {"timeseries": aggregated_capacity, "colour": "darkgreen", "label": "Capacity"}
    ]

    # Create individual effort timeseries according to project status
    projects = (  # Traces are cumulative
        ("Tentative", "firebrick", ["Tentative", "Confirmed", "Active", "Maintenance"]),
        ("Confirmed", "orange", ["Confirmed", "Active", "Maintenance"]),
        ("Maintenance", "purple", ["Active", "Maintenance"]),
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
    vareas: tuple[tuple[tuple[str, str], str], ...] = (
        (("Capacity", "Confirmed project effort"), "green"),
        (("Maintenance project effort", "Active project effort"), "purple"),
        (("Confirmed project effort", "Maintenance project effort"), "yellow"),
        (("Tentative project effort", "Confirmed project effort"), "red"),
    )

    plot = create_timeseries_plot(
        title="Project effort and team capacity over time",
        traces=traces,
        x_range=x_range,
        vareas=vareas,
    )

    allocations = timeseries.get_allocation_timeseries(start_date, end_date)
    individual_plots = []
    vareas = (
        (("Capacity", ""), "green"),
        (("", "Capacity"), "red"),
    )

    for name in capacities.columns:
        traces = [
            {
                "timeseries": capacities[name],
                "colour": "darkgreen",
                "label": "Capacity",
            }
        ]
        allocation = allocations[name]
        all_projects = allocation.sum(axis=1)
        traces.append(
            {
                "timeseries": all_projects,
                "colour": None,
                "label": "",
            }
        )

        colours = cycle(["red", "purple", "yellow", "navy"])
        for project in allocation.columns:
            traces.append(
                {
                    "timeseries": allocation[project],
                    "colour": next(colours),
                    "label": project,
                }
            )
        individual_plots.append(
            create_timeseries_plot(
                title=name,
                traces=traces,
                x_range=x_range,
                vareas=vareas,
                height=150,
                legend_loc="top_right",
            )
        )

    return plot, individual_plots


def create_capacity_planning_layout() -> Row:
    """Create the capacity planning plot in layout with widgets.

    Creates the capacity planning plot plus the associated widgets used to control the
    data displayed in the plot.

    Returns:
        A Row object (the Row containing a Column of widgets and the plot).
    """
    start, end = timezone.now(), timezone.now() + timedelta(days=365)
    # Min and max dates are three years before and ahead of current date
    min_date, max_date = start - timedelta(days=1095), start + timedelta(days=1095)

    # Get the plot to display (it is created with all data, but only the dates
    # in the x_range provided are shown)
    plot, individual_plots = create_capacity_planning_plot(
        start_date=min_date, end_date=max_date, x_range=(start, end)
    )
    plot.title.text_font_size = "20px"  # type: ignore[union-attr]
    plot.yaxis.axis_label = "Capacity and Effort (FTE)"

    # Create a crosshair to show in all plots, synchronised
    height = Span(dimension="height", line_dash="dotted", line_width=2)
    crosshair = CrosshairTool(overlay=height, dimensions="height")

    plot.add_tools(crosshair)
    for i, plt in enumerate(individual_plots):
        plt.add_tools(crosshair)

        plt.y_range = Range1d(0, 1)  # type: ignore[arg-type]
        plt.yaxis.axis_label = "Cap&Eff (FTE)"
        plt.xaxis.axis_label = None
        plt.title.text_font_size = "20px"  # type: ignore[union-attr]

        # --- Remove internal border padding to eliminate the visual gap ---
        plt.min_border_top = 0
        plt.min_border_bottom = 0

        # --- Hide x-axis on all plots except the last two ---
        if i < len(individual_plots) - 2:
            plt.xaxis.major_label_text_font_size = "0pt"  # Hide tick labels
            plt.xaxis.major_tick_line_color = None  # Hide tick marks
            plt.xaxis.minor_tick_line_color = None  # Hide minor ticks

    # Create layout with common plot at the top and individual ones in a grid
    # below
    plot_layout = column(  # type: ignore[call-overload]
        [
            plot,
            gridplot(  # type: ignore[call-overload]
                individual_plots, ncols=2, sizing_mode="stretch_width"
            ),
        ],
        sizing_mode="stretch_width",
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
    capacities = timeseries.get_capacity_timeseries(
        start_date=start_date, end_date=end_date
    )
    capacity_timeseries = capacities.sum(axis=1)

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

    # Create button to set plots to default year
    last_year_button = Button(
        label="Last year",
    )
    widgets.add_callback_to_button(
        button=last_year_button,
        dates=(start, max_date),
        plot=timeseries_plot,
        include_future_dates=False,
    )
    widgets.add_bar_callback_to_button(
        button=last_year_button,
        dates=get_calendar_year_dates(),
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
        column(last_year_button, calendar_button, financial_button),
        column(
            timeseries_plot,
            bar_plot,
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
    )
    return plot_layout


def get_time_vertical_line(location: datetime, colour: str = "black") -> Span:
    """Create a vertical line to indicate the specified time on the plots.

    Args:
        location: The timestamp to position the vertical line.
        colour: Colour for the lne. Defaults to black.

    Returns:
        A Span object representing the vertical line for the specified time.
    """
    now_line = Span(
        location=location,
        dimension="height",
        line_color=colour,
        line_dash="dashed",
        line_width=1,
    )
    return now_line


def _expected_days_used(  # type: ignore[explicit-any]
    project: models.Project,
) -> pd.Series:
    """Create the time series with the expected time used in the project."""
    if not project.phases.exists():
        return pd.Series()

    _expected = []
    cumsum = 0.0
    for phase in project.phases.all():
        _expected.append(
            {"date": pd.to_datetime(phase.start_date, utc=True), "value": cumsum}
        )
        cumsum += phase.days

    assert project.end_date
    _expected.append(
        {"date": pd.to_datetime(project.end_date, utc=True), "value": cumsum}
    )
    expected = (
        pd.DataFrame(_expected).set_index("date")["value"].resample("D").interpolate()
    )

    return expected


def _actual_days_used(  # type: ignore[explicit-any]
    project: models.Project,
) -> pd.Series:
    """Create the time series with the actual time used in the project."""
    _usage = pd.DataFrame.from_records(
        project.timeentry_set.all().values("start_time", "end_time")
    )
    if _usage.empty:
        return pd.Series()

    _usage["time_used"] = (_usage["end_time"] - _usage["start_time"]).dt.total_seconds()
    usage = (
        _usage.set_index("start_time")
        .drop("end_time", axis="columns")
        .groupby(pd.Grouper(freq="D"))
        .sum()
        .cumsum()["time_used"]
    )
    usage.index.name = None
    usage = usage / (7 * 3600)

    return usage


def _actual_days_charged(  # type: ignore[explicit-any]
    project: models.Project,
) -> pd.Series:
    """Create the time series with the actual time used in the project."""
    _charges = pd.DataFrame.from_records(
        models.MonthlyCharge.objects.filter(project=project).values("date", "amount")
    )
    if _charges.empty:
        return pd.Series()

    # We add an extra point at the end, so the trace always renders.
    _charges = pd.concat(
        [
            _charges,
            pd.DataFrame(
                {"date": timezone.now().today(), "amount": 0.0}, index=[len(_charges)]
            ),
        ]
    )

    # Now accumulate the charges
    _charges["amount"] = _charges["amount"].astype(float)
    _charges["date"] = pd.to_datetime(_charges["date"], utc=True)
    charges = (
        _charges.set_index("date")
        .groupby(pd.Grouper(freq="D"))
        .sum()
        .cumsum()["amount"]
    )

    # Finally, we calculate the corresponding days
    budget = pd.DataFrame.from_records(
        project.funding_source.all().values("budget", "daily_rate")
    )
    total_budget = budget["budget"].sum()
    weighted_daily_rate = (budget["budget"] * budget["daily_rate"]).sum() / total_budget
    charges = charges / float(weighted_daily_rate)

    return charges


def create_project_evolution_plot(project: models.Project) -> figure | None:
    """Create plot with the time evolution of usage and charges."""
    # Expected, commulative use, homogeneous over each phase
    traces = []
    if not (expected := _expected_days_used(project)).empty:
        traces.append(
            {
                "timeseries": expected,
                "label": "Expected trend",
                "colour": "red",
            },
        )

    # Actual usage, based on time records, if any
    if not (actual := _actual_days_used(project)).empty:
        traces.append({"timeseries": actual, "label": "Actual usage", "colour": "blue"})

    # Charges made, for those projects with charges
    if not (charges := _actual_days_charged(project)).empty:
        traces.append(
            {"timeseries": charges, "label": "Charged days", "colour": "green"}
        )

    if not traces:
        return None

    plot = create_timeseries_plot(
        "Project evolution",
        traces,
        height=400,
        legend_loc="bottom_right",
    )
    plot.yaxis.axis_label = "Days"

    for phase in project.phases.all():
        plot.add_layout(get_time_vertical_line(pd.to_datetime(phase.start_date)))
    assert project.end_date
    plot.add_layout(get_time_vertical_line(pd.to_datetime(project.end_date)))
    plot.add_layout(get_time_vertical_line(datetime.now(), colour="grey"))

    return plot


def create_project_evolution_layout(project: models.Project) -> Row | None:
    """Add the evolution plot to a layout.

    Args:
        project: Project object the layout is about.

    Returns:
        The layout with the plot.
    """
    plot = create_project_evolution_plot(project)
    if not plot:
        return None
    plot_layout = row(plot, sizing_mode="stretch_width")
    return plot_layout


def create_pie_chart(category_name: str, data: dict[str, int]) -> figure:
    """Create a pie chart.

    Args:
        category_name: The name of the category being displayed.
        data: The data being displayed.

    Returns:
        The Bokeh figure for the pie chart.
    """
    source = (
        pd.Series(data)
        .reset_index(name="value")
        .rename(columns={"index": category_name})
    )
    source["angle"] = source["value"] / source["value"].sum() * 2 * pi
    source["colour"] = Category20c[len(data)]

    plot = figure(
        title=f"Projects per {category_name.lower()}",
        toolbar_location=None,
        x_range=(-0.5, 1.0),  # type: ignore[arg-type]
    )

    plot.wedge(
        x=0,
        y=1,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        radius=0.4,
        line_color="white",
        fill_color="colour",
        legend_field=category_name,
        source=source,
    )

    plot.add_tools(HoverTool(tooltips=f"@{category_name}: @value"))

    plot.axis.axis_label = None
    plot.axis.visible = False
    plot.grid.grid_line_color = None

    return plot


def create_analytics_layout() -> figure:
    """Create the analytics charts in a layout with widgets.

    Creates the project analytics charts plus the associated widgets.

    Returns:
        A layout containing each of the analytics plots.
    """
    # Generate the list of plots we wish to display
    plots = []
    today = date.today()
    one_year_ago = today - timedelta(days=365)

    fcn_map = {
        "Department": analytics.get_num_projects_per_department,
        "Faculty": analytics.get_num_projects_per_faculty,
    }
    for division, get_num_projects_per_division in fcn_map.items():
        data = get_num_projects_per_division(
            analytics.get_projects_active_between(one_year_ago, today)
        )
        plots.append(create_pie_chart(category_name=division, data=data))

    # Arrange the plots into a two-column grid layout
    layout = column(  # type: ignore[call-overload]
        [
            gridplot(  # type: ignore[call-overload]
                plots, ncols=2, sizing_mode="stretch_width"
            ),
        ],
        sizing_mode="stretch_width",
    )
    return layout


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
