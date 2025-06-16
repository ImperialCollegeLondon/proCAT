"""Tests for the plots module."""

from datetime import datetime, timedelta

import pandas as pd
import pytest


def test_update_timeseries():
    """Test the update_timeseries function."""
    from main import models, plots

    dates = pd.bdate_range(
        pd.Timestamp(datetime.now()),
        pd.Timestamp(datetime.now() + timedelta(14)),
        inclusive="left",
    )
    timeseries = pd.Series(0.0, index=dates)
    capacity = models.Capacity(value=0.5, start_date=datetime.now().date())
    capacity.end_date = datetime.now().date() + timedelta(7)
    assert timeseries.value_counts()[0.0] == 10

    timeseries = plots.update_timeseries(capacity, timeseries, "value")
    assert timeseries.value_counts()[capacity.value] == 5


@pytest.mark.django_db
@pytest.mark.usefixtures("department", "user", "activity_code")
def test_get_effort_timeseries():
    """Test the get_effort_timeseries function."""
    from main import models, plots

    plot_start_date, plot_end_date = datetime.now(), datetime.now() + timedelta(28)
    department = models.Department.objects.get(name="ICT")
    user = models.User.objects.get(username="testuser")
    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        status="Active",
        start_date=datetime.now().date() + timedelta(7),
        end_date=datetime.now().date() + timedelta(14),
    )

    activity_code = models.ActivityCode.objects.get(code="1234")
    funding = models.Funding.objects.create(
        project=project,
        source="External",
        project_code="1234",
        activity_code=activity_code,
        budget=1000.00,
        daily_rate=100.00,
    )

    timeseries = plots.get_effort_timeseries(plot_start_date, plot_end_date)
    assert isinstance(timeseries, pd.Series)

    effort = funding.budget / funding.daily_rate
    effort_per_day = effort / project.total_working_days
    n_entries = timeseries.value_counts()[effort_per_day]
    assert n_entries == 5


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_get_capacity_timeseries(user):
    """Test the get_effort_timeseries function."""
    from main import models, plots

    capacity = models.Capacity.objects.create(
        user=user, value=0.5, start_date=datetime.now().date() + timedelta(14)
    )
    plot_start_date, plot_end_date = datetime.now(), datetime.now() + timedelta(28)

    timeseries = plots.get_capacity_timeseries(plot_start_date, plot_end_date)
    assert isinstance(timeseries, pd.Series)

    n_entries = timeseries.value_counts()[capacity.value]
    assert n_entries == 10
