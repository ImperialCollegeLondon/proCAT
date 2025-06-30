"""Timeseries for Capacity and Project data for plotting."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from django.db.models import F, Window
from django.db.models.functions import Coalesce, Lead

from . import models


def update_timeseries(
    timeseries: pd.Series[float],
    object: models.Project | models.Capacity,
    attr_name: str,
) -> pd.Series[float]:
    """Update the initialized timeseries with value from a Model object.

    The dates for the Model are used to index the timeseries. The value added is
    specified by the attr_name.

    TODO: For advanced capacity planning, keep separate Project and User timeseries
    so these can be plotted individually.

    Args:
        timeseries: the Pandas series containing the Project or Capacity data with
            the dates of the plotting period as the index
        object: the Project or Capacity object used to update the timeseries
        attr_name: the name of the attribute representing the value to add to the
            timeseries (i.e. 'value' or 'effort_per_day')

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


def get_effort_timeseries(start_date: datetime, end_date: datetime) -> pd.Series[float]:
    """Get the timeseries data for aggregated project effort.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

    Returns:
        Pandas series of aggregated effort with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )
    # filter Projects to ensure dates exist and overlap with timeseries dates
    projects = list(
        models.Project.objects.filter(
            start_date__lt=end_date.date(),
            end_date__gte=start_date.date(),
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


def get_capacity_timeseries(
    start_date: datetime, end_date: datetime
) -> pd.Series[float]:
    """Get the timeseries data for aggregated user capacities.

    A user may have multiple capacity entries associated. In this case, we assign the
    'end date' for the capacity entry as the start date of the next capacity. If there
    is no subsequent capacity entry, the 'end date' is the end of the plotting period.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period

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
