"""Plots for displaying database data."""

from datetime import datetime

import pandas as pd
from django.db.models import Model, Q

from . import models


def update_timeseries(
    object: Model,
    timeseries: pd.Series,
    attr_name: str,
) -> pd.Series:
    """Update the initialized timeseries with data from a Model object.

    By specifying attr_name (e.g. Capacity.value), this value is added to the timeseries
    using the start_date and end_date attributes to index the timeseries. Dates are
    ignored if they do not exist within the period specified for plotting.

    Returns:
        Pandas series representing the updated timeseries with values from the Model.
    """
    object_dates = pd.bdate_range(
        start=object.start_date, end=object.end_date, inclusive="left"
    )
    # get intersection between the Model dates and the plotting dates
    index = timeseries.index.intersection(object_dates)
    timeseries[index] += float(getattr(object, attr_name))
    return timeseries


def get_effort_timeseries(start_date: datetime, end_date: datetime) -> pd.Series:
    """Get the timeseries data for project effort.

    Only relevant for 'Active' and 'Not started' projects, projects that fit within the
    selected time period, and projects with funding associated. Returns time series
    with aggregated effort per day over all projects, considering only business days.

    Returns:
        Pandas series of aggregated effort with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )
    # filter Project objects according to status, dates and whether they have funding
    status_include = ["Not started", "Active"]
    projects = models.Project.objects.all().filter(
        Q(start_date__gte=start_date.date()) | Q(end_date__lt=end_date.date()),
        status__in=status_include,
    )
    projects = [project for project in projects if project.funding_source.exists()]

    # initialize time series
    timeseries = pd.Series(0.0, index=dates)

    for project in projects:
        timeseries = update_timeseries(project, timeseries, "effort_per_day")

    return timeseries


def get_capacity_timeseries(start_date: datetime, end_date: datetime) -> pd.Series:
    """Get the timeseries data for aggregated user capacities.

    A user may have multiple capacity entries associated. In this case, we assign the
    'end date' for the capacity entry as the start date of the next capacity. If there
    is no subsequent capacity entry, the 'end date' is the end of the time period
    selected.

    Returns:
        Pandas series of aggregated capacities with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )
    capacities = models.Capacity.objects.all().filter(start_date__lte=end_date.date())
    users = capacities.values_list("user__username", flat=True).distinct()

    # initialize time series
    timeseries = pd.Series(0.0, index=dates)

    for user in users:
        # retrieve capacity objects for each user and sort by start date
        user_capacities = capacities.filter(user__username=user)
        user_capacities = sorted(user_capacities, key=lambda x: x.start_date)

        for idx, capacity in enumerate(user_capacities):
            # assign end date depending on whether future capacity object exists
            if idx != len(user_capacities) - 1:
                capacity.end_date = user_capacities[idx + 1].start_date
            else:
                capacity.end_date = end_date.date()

            timeseries = update_timeseries(capacity, timeseries, "value")

    return timeseries
