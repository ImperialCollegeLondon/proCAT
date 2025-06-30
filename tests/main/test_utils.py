"""Tests for the utils module."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.django_db
def test_create_destroy_activity_codes():
    """Roundtrip check of creation and destruction of activity codes."""
    from main import models, utils

    assert len(models.ActivityCode.objects.all()) == len(utils.ACTIVITY_CODES)
    utils.destroy_activities()
    assert len(models.ActivityCode.objects.all()) == 0
    utils.create_activities()
    assert len(models.ActivityCode.objects.all()) == len(utils.ACTIVITY_CODES)


@pytest.mark.django_db
def test_get_logged_hours(user, project):
    """Test get_logged_hours function."""
    from main.models import TimeEntry
    from main.utils import get_logged_hours

    # Create a time entries for a project
    start_time_1 = datetime(2025, 4, 1, 11, 0)
    end_time_1 = start_time_1 + timedelta(hours=5)

    start_time_2 = datetime(2025, 6, 2, 10, 0)
    end_time_2 = start_time_2 + timedelta(hours=4.2)

    start_time_3 = datetime(2025, 6, 3, 9, 0)
    end_time_3 = start_time_3 + timedelta(hours=6.5)

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time_1,
        end_time=end_time_1,
    )
    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time_2,
        end_time=end_time_2,
    )
    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time_3,
        end_time=end_time_3,
    )

    entries = TimeEntry.objects.filter(user=user)
    total_hours, project_work_summary = get_logged_hours(entries)

    # Expected values
    expected_hours = 5 + 4.2 + 6.5  # ~15.7
    # Assuming 7 hours/workday, we convert total hours
    expected_days = round(expected_hours / 7, 1)  # ~2.2
    expected_summary = f"{project.name}: {expected_days} days"

    assert round(total_hours, 1) == round(expected_hours, 1)
    assert project_work_summary == expected_summary


@pytest.mark.django_db
def test_get_current_and_last_month_start():
    """Test get_current_and_last_month_start function."""
    from main.utils import get_current_and_last_month

    date = datetime(2025, 6, 15)  # Fixed date for testing
    last_month_start, last_month_name, current_month_start, current_month_name = (
        get_current_and_last_month(date=date)
    )
    # Last month is May 2025
    assert last_month_start == datetime(2025, 5, 1)
    assert last_month_name == "May"
    # Current month is June 2025
    assert current_month_start == datetime(2025, 6, 1)
    assert current_month_name == "June"
