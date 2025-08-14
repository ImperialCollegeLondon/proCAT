"""Timeseries for generating ProCAT plots."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
from django.db.models import (
    ExpressionWrapper,
    F,
    FloatField,
    Sum,
    Value,
    Window,
)
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
    for proj in projects:
        timeseries = update_timeseries(timeseries, proj, "effort_per_day")

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


def get_cost_recovery_timeseries(
    dates: list[tuple[date, date]],
) -> tuple[pd.Series[float], list[float]]:
    """Get the cost recovery timeseries for the previous year.

    For each month in the past year, this function aggregates all monthly charges and
    divides this by the daily rate (dependent on funding source) and the number of
    working days. This value is summed across all funding sources and added to the
    timeseries.

    Args:
        dates: list of tuples (from oldest to most recent) containing dates for all
            months of the previous year; each tuple contains two dates for the first
            and last date of the month

    Returns:
        Tuple of Pandas series containing cost recovery timeseries data and a list of
        monthly totals.
    """
    date_range = pd.bdate_range(
        start=dates[0][0],
        end=dates[-1][1],
        inclusive="both",
    )
    # initialize timeseries
    timeseries = pd.Series(0.0, index=date_range)

    # store monthly totals for bar plot
    monthly_totals = []

    for month in dates:
        month_dates = pd.bdate_range(start=month[0], end=month[1], inclusive="both")
        n_working_days = len(month_dates)
        monthly_charges = models.MonthlyCharge.objects.filter(date=month[0])
        monthly_total = monthly_charges.aggregate(Sum("amount"))["amount__sum"]

        # group by funding
        charges = (
            monthly_charges.values("funding")
            .annotate(total=Sum("amount"))  # get total Amount across monthly charges
            .annotate(  # divide total by daily rate and working days
                recovered=ExpressionWrapper(
                    F("total") * Value(1.0) / F("funding__daily_rate") / n_working_days,
                    output_field=FloatField(),
                )
            )
        )

        # aggregate across all funding sources (defaults to 0 if None)
        funding_total = charges.aggregate(Sum("recovered"))["recovered__sum"] or 0
        timeseries[month_dates] += funding_total  # Update timeseries

        # record total for the month
        monthly_totals.append(float(monthly_total) if monthly_total else 0.0)

    return timeseries, monthly_totals


def get_project_effort_timeseries(
    start_date: datetime, end_date: datetime, project: str
) -> pd.Series[float]:
    """Get effort timeseries data for a specific project.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period
        project: name of the project to filter by

    Returns:
        Pandas series of project-specific effort with date range as index.
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
            name=project,
        )
    )

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for project in projects:
        timeseries = update_timeseries(timeseries, project, "effort_per_day")

    return timeseries


def get_user_effort_timeseries(
    start_date: datetime, end_date: datetime, user: str
) -> pd.Series[float]:
    """Get effort timeseries data for a specific user.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period
        user: username of the user to filter by

    Returns:
        Pandas series of user-specific effort with date range as index.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left"
    )

    # filter capacity for users
    capacities = list(
        models.Capacity.objects.filter(
            start_date__lt=end_date.date(),
            start_date__isnull=False,
            user__username=user,
        )
    )

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for capacity in capacities:
        timeseries = update_timeseries(timeseries, capacity, "value")

    return timeseries
