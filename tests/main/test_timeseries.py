"""Tests for the timeseries module."""

from datetime import datetime, time, timedelta

import pandas as pd
import pytest


def test_update_timeseries():
    """Test the update_timeseries function."""
    from main import models, timeseries

    dates = pd.bdate_range(
        pd.Timestamp(datetime.now()),
        pd.Timestamp(datetime.now() + timedelta(14)),
        inclusive="left",
    )
    ts = pd.Series(0.0, index=dates)
    capacity = models.Capacity(value=0.5, start_date=datetime.now().date())
    capacity.end_date = datetime.now().date() + timedelta(7)
    assert ts.value_counts()[0.0] == 10

    ts = timeseries.update_timeseries(ts, capacity, "value")
    assert ts.value_counts()[capacity.value] == 5


@pytest.mark.django_db
@pytest.mark.parametrize(
    ["start_date", "end_date", "plot_start_date", "plot_end_date"],
    [
        [
            datetime.now().date() + timedelta(7),
            datetime.now().date() + timedelta(14),
            datetime.now(),
            datetime.now() + timedelta(21),
        ],
        [
            datetime.now().date(),
            datetime.now().date() + timedelta(21),
            datetime.now() + timedelta(7),
            datetime.now() + timedelta(14),
        ],
        [
            datetime.now().date(),
            datetime.now().date() + timedelta(20),
            datetime.now() + timedelta(4),
            datetime.now() + timedelta(30),
        ],
    ],
)
def test_get_effort_timeseries(
    department,
    user,
    analysis_code,
    start_date,
    end_date,
    plot_start_date,
    plot_end_date,
):
    """Test the get_effort_timeseries function."""
    from main import models, timeseries

    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        status="Active",
        start_date=start_date,
        end_date=end_date,
    )

    funding = models.Funding.objects.create(
        project=project,
        source="External",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        budget=1000.00,
        daily_rate=100.00,
    )

    ts = timeseries.get_effort_timeseries(plot_start_date, plot_end_date)
    assert isinstance(ts, pd.Series)

    effort = funding.budget / funding.daily_rate
    effort_per_day = effort / project.total_working_days
    n_entries = ts.value_counts()[effort_per_day]

    # get intersecting dates
    project_days = pd.bdate_range(start_date, end_date, inclusive="left")
    plot_days = pd.bdate_range(plot_start_date, plot_end_date, inclusive="left")
    n_days = len(project_days.intersection(plot_days))
    assert n_entries == n_days


@pytest.mark.django_db
def test_get_capacity_timeseries(user):
    """Test the get_capacity_timeseries function."""
    from main import models, timeseries

    capacity_A = models.Capacity.objects.create(
        user=user, value=0.5, start_date=datetime.now().date()
    )
    capacity_B = models.Capacity.objects.create(
        user=user, value=0.7, start_date=datetime.now().date() + timedelta(7)
    )
    plot_start_date, plot_end_date = datetime.now(), datetime.now() + timedelta(28)
    ts = timeseries.get_capacity_timeseries(plot_start_date, plot_end_date)
    assert isinstance(ts, pd.Series)
    assert ts.value_counts()[capacity_A.value] == 5
    assert ts.value_counts()[capacity_B.value] == 15


@pytest.mark.django_db
def test_get_cost_recovery_timeseries(department, user, analysis_code):
    """Test the get_cost_recovery_timeseries function."""
    from main import models, report, timeseries, utils

    today = datetime.today().date()

    # Create a project and associated funding
    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=today - timedelta(days=365),
        end_date=today,
        status="Active",
        charging="Actual",
    )
    # Create funding objects (monthly charge will be created for each)
    models.Funding.objects.create(  # expires first
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=today + timedelta(15),
        budget=500.00,
        daily_rate=400.00,
    )  # 1.25 days worth of funds
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G56789",
        analysis_code=analysis_code,
        expiry_date=today + timedelta(30),
        budget=5000.00,
        daily_rate=400.00,
    )

    # Create time entries (1.5 days total) in last month
    end_last_month = today.replace(day=1) - timedelta(days=1)
    start_last_month = end_last_month.replace(day=1)
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime.combine(start_last_month, time(hour=9)),
        end_time=datetime.combine(start_last_month, time(hour=16)),
    )  # 7 hours total
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime.combine(start_last_month, time(hour=10)),
        end_time=datetime.combine(start_last_month, time(hour=13, minute=30)),
    )  # 3.5 hours total

    # Create monthly charges
    report.create_actual_monthly_charges(project, start_last_month, end_last_month)

    # Create an additional time entry that will be added to the timeseries but NOT
    # the monthly charge total
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime.combine(start_last_month, time(hour=11)),
        end_time=datetime.combine(start_last_month, time(hour=18)),
    )  # 7 hours total

    # Create cost recovery timeseries
    dates = utils.get_month_dates_for_previous_years()
    ts, charge_totals = timeseries.get_cost_recovery_timeseries(dates)

    # Get expected value
    n_days = round((pd.Timestamp(start_last_month).days_in_month / 365) * 220)
    expected_value = 17.5 / 7 / n_days
    assert isinstance(ts, pd.Series)
    assert ts.value_counts()[expected_value] == len(
        pd.bdate_range(start=start_last_month, end=end_last_month, inclusive="both")
    )

    # £500 charged to funding A; £100 charged to funding B
    assert charge_totals[-1] == 600.00


@pytest.mark.django_db
def test_get_cost_recovery_timeseries_equal_to_num_people(
    department, user, analysis_code
):
    """Test the get_cost_recovery_timeseries function when all time in project work.

    Tests the value given is equal to the number of people working if all time is
    invested in project work.
    """
    from main import models, report, timeseries, utils

    today = datetime.today().date()

    # Create a project and associated funding
    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=today - timedelta(days=365),
        end_date=today + timedelta(days=365),
        status="Active",
        charging="Actual",
    )
    # Create funding objects
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=today + timedelta(15),
        budget=1900.00,
        daily_rate=200.00,
    )
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=today + timedelta(30),
        budget=540000.00,
        daily_rate=123.00,
    )

    end_last_month = today.replace(day=1) - timedelta(days=1)
    start_last_month = end_last_month.replace(day=1)
    n_working_days = round((pd.Timestamp(start_last_month).days_in_month / 365) * 220)

    # Create 2 time entries where number of hours is exactly equal to the full capacity
    # of an individual (7 * n_working_days)
    start_time = datetime.combine(start_last_month, time(hour=9))
    end_time = start_time + timedelta(hours=7 * n_working_days)
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    # Create monthly charges
    report.create_actual_monthly_charges(project, start_last_month, end_last_month)

    # Create cost recovery timeseries
    dates = utils.get_month_dates_for_previous_years()
    ts = timeseries.get_cost_recovery_timeseries(dates)[0]

    # Expected value for 2 individuals working full-time on projects would be 2.0
    assert ts.value_counts()[2.0] == len(
        pd.bdate_range(start_last_month, end_last_month, inclusive="both")
    )