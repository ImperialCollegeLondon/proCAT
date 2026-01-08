"""Timeseries for generating ProCAT plots."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from django.db.models import (
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Window,
)
from django.db.models.functions import Coalesce, Lead

from procat.settings.settings import TIME_ZONE, WORKING_DAYS

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
        tz=TIME_ZONE,
    )
    # get intersection between the Model dates and the plotting dates
    index = timeseries.index.intersection(object_dates)
    timeseries[index] += float(getattr(object, attr_name))
    return timeseries


def get_effort_timeseries(
    start_date: datetime, end_date: datetime, project_statuses: list[str] | None = None
) -> pd.Series[float]:
    """Get the timeseries data for aggregated project effort.

    Args:
        start_date: datetime object representing the start of the plotting period
        end_date: datetime object representing the end of the plotting period
        project_statuses: a list of project status values to filter the Project results
            by (e.g. ['Active', 'Confirmed']), or None if no filter applied

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
        ).filter(  # apply status filter if supplied
            Q(status__in=project_statuses) if project_statuses else Q()
        )
    )
    projects = [project for project in projects if project.funding_source.exists()]

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for project in projects:
        timeseries = update_timeseries(timeseries, project, "effort_per_day")

    return timeseries


def get_internal_effort_timeseries(
    start_date: datetime, end_date: datetime
) -> pd.Series[float]:
    """Get the timeseries data for projects that are not included in MonthlyCharges.

    This includes internal projects that are not charged to an external
    funding source.

    Args:
        start_date: datetime object representing the start of the
            plotting period
        end_date: datetime object representing the end of the
            plotting period

    Returns:
        Pandas Series containing internal effort timeseries data.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left", tz=TIME_ZONE
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
    projects = [
        project
        for project in projects
        if project.funding_source.filter(source="Internal").exists()
    ]

    # initialize timeseries
    timeseries = pd.Series(0.0, index=dates)
    for project in projects:
        timeseries = update_timeseries(timeseries, project, "effort_per_day")

    return timeseries


def get_team_members_timeseries(
    start_date: datetime, end_date: datetime
) -> pd.Series[float]:
    """Get number of active team members with capacity above zero in a given period.

    The number of team members is time dependent.

    Args:
        start_date: datetime object representing the start of the plotting
            period
        end_date: datetime object representing the end of the plotting period

    Returns:
        The number of active team members with capacity above zero over the time period.
    """
    dates = pd.bdate_range(
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left", tz=TIME_ZONE
    )

    capacities = list(
        models.Capacity.objects.filter(start_date__lte=end_date.date(), value__gt=0)  # type: ignore [no-redef]
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

    # By setting the capacity value to 1, we are effectively counting team members
    # active in those dates.
    for capacity in capacities:
        capacity.value = 1.0
        timeseries = update_timeseries(timeseries, capacity, "value")

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
        pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive="left", tz=TIME_ZONE
    )
    # if multiple capacities for a user, end_date is start_date of next capacity object
    # if no subsequent capacity, then end_date is plotting period end_date
    capacities = list(
        models.Capacity.objects.filter(start_date__lte=end_date.date())  # type: ignore [no-redef]
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

    For each month in the past year, this function aggregates all time entries and
    divides this by the number of working days. This value is added to the time series.
    The total monthly charges for the month are also recorded.

    Args:
        dates: list of tuples (from oldest to most recent) containing dates for all
            months of the previous year; each tuple contains two dates for the first
            and last date of the month

    Returns:
        Tuple of Pandas series containing cost recovery timeseries data and a list of
        monthly totals.
    """
    date_range = pd.bdate_range(
        start=dates[0][0], end=dates[-1][1], inclusive="both", tz=TIME_ZONE
    )
    # initialize timeseries
    timeseries = pd.Series(0.0, index=date_range)

    # store monthly totals for bar plot
    monthly_totals = []

    for month in dates:
        # record charge total for the month
        month_dates = pd.bdate_range(
            start=month[0], end=month[1], inclusive="both", tz=TIME_ZONE
        )
        n_working_days = round(
            (pd.Timestamp(month[0]).days_in_month / 365) * WORKING_DAYS
        )
        monthly_charges = models.MonthlyCharge.objects.filter(date=month[0])
        monthly_total = monthly_charges.aggregate(Sum("amount"))["amount__sum"]
        monthly_totals.append(float(monthly_total) if monthly_total else 0.0)

        # calculate the total time entries for the month, and work out the time
        # logged (recovered) per day across all projects
        start_time = datetime.combine(month[0], datetime.min.time())
        end_time = datetime.combine(month[1], datetime.min.time())
        entries = (
            models.TimeEntry.objects.filter(
                start_time__gte=start_time, start_time__lt=end_time
            )
        ).annotate(
            duration=ExpressionWrapper(
                (F("end_time") - F("start_time")), output_field=DurationField()
            ),
        )
        total_duration = entries.aggregate(Sum("duration"))[
            "duration__sum"
        ] or timedelta(0)
        recovered_per_day = total_duration.total_seconds() / 3600 / 7 / n_working_days
        timeseries[month_dates] += recovered_per_day  # Update timeseries

    return timeseries, monthly_totals
