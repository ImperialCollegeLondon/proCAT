"""Plots for displaying database data."""

from datetime import datetime

import bokeh
import pandas as pd
from bokeh.models import ColumnDataSource
<<<<<<< HEAD

from . import timeseries
=======
from bokeh.plotting import figure
from django.db.models import F, Q, Window
from django.db.models.functions import Coalesce, Lead

from . import models


def get_bokeh_version() -> str:
    """Get Bokeh version for HTML script tags."""
    return bokeh.__version__


def update_timeseries(
    timeseries: pd.Series, object: models.Project | models.Capacity, attr_name: str
) -> pd.Series:
    """Update the initialized timeseries with value from a Model object.

    The dates for the Model are used to index the timeseries. The value added is
    specified by the attr_name.

    TODO: For advanced capacity planning, keep separate Project and User timeseries
    so these can be plotted individually.

    Returns:
        Pandas series containing updated timeseries data.
    """
    object_dates = pd.bdate_range(
        start=object.start_date,
        end=object.end_date,  # type: ignore[union-attr]
        inclusive="left",
    )
    # get intersection between the Model dates and the plotting dates
    index = timeseries.index.intersection(object_dates)
    timeseries[index] += float(getattr(object, attr_name))
    return timeseries


def get_effort_timeseries(start_date: datetime, end_date: datetime) -> pd.Series:
    """Get the timeseries data for aggregated project effort.

    Returns:
        Pandas series of aggregated effort with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )
    # filter Projects to ensure dates exist and overlap with timeseries dates
    projects = list(
        models.Project.objects.filter(
            Q(start_date__gte=start_date.date()) | Q(end_date__lt=end_date.date()),
            start_date__isnull=False,
            end_date__isnull=False,
        )
    )
    projects = [project for project in projects if project.funding_source.exists()]

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for project in projects:
        timeseries = update_timeseries(timeseries, project, "effort_per_day")

    return timeseries


def get_capacity_timeseries(start_date: datetime, end_date: datetime) -> pd.Series:
    """Get the timeseries data for aggregated user capacities.

    A user may have multiple capacity entries associated. In this case, we assign the
    'end date' for the capacity entry as the start date of the next capacity. If there
    is no subsequent capacity entry, the 'end date' is the end of the plotting period.

    Returns:
        Pandas series of aggregated capacities with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )
    # if multiple capacities for a user, end_date is start_date of next capacity object
    # if no subsequent capacity, then end_date is plotting period end_date
    capacities = list(
        models.Capacity.objects.filter(start_date__lte=end_date.date())
        .annotate(
            end_date=Window(
                expression=Lead("start_date"),  # get start date of next capacity
                order_by=F("start_date").asc(),  # orders by ascending start date
                partition_by="user__username",
            )
        )
        .annotate(end_date=Coalesce("end_date", end_date.date()))
    )

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for capacity in capacities:
        timeseries = update_timeseries(timeseries, capacity, "value")

    return timeseries
>>>>>>> 0ab2232 (Add initial capacity planning view)


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
    plot.legend.click_policy = "hide"
    return plot
