"""Tests for the utils module."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.django_db
def test_create_destroy_analysis_codes():
    """Roundtrip check of creation and destruction of analysis codes."""
    from main import models, utils

    assert len(models.AnalysisCode.objects.all()) == len(utils.ANALYSIS_CODES)
    utils.destroy_analysis()
    assert len(models.AnalysisCode.objects.all()) == 0
    utils.create_analysis()
    assert len(models.AnalysisCode.objects.all()) == len(utils.ANALYSIS_CODES)


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


@pytest.mark.django_db
def test_get_budget_status():
    """Test get_budget_status function."""
    from main.models import Department, Funding, Project
    from main.utils import get_budget_status

    today = datetime.today().date()

    # Create a department
    department = Department.objects.create(name="Test Department")

    # Create a project
    project = Project.objects.create(name="Test Project", department=department)

    # Create some funding entries
    funding1 = Funding.objects.create(
        project=project,
        budget=10000,
        expiry_date=today + timedelta(days=30),  # Not expired
    )
    funding2 = Funding.objects.create(
        project=project,
        budget=5000,
        expiry_date=today - timedelta(days=30),  # Expired
    )
    funding3 = Funding.objects.create(
        project=project,
        budget=-1000,
        expiry_date=today + timedelta(days=30),  # Ran out but not expired
    )
    funding4 = Funding.objects.create(
        project=project,
        budget=2000,
        expiry_date=today - timedelta(days=30),  # Expired but has budget
    )

    funds_ran_out_not_expired, funding_expired_budget_left = get_budget_status(
        date=today
    )

    # Check the results
    assert funds_ran_out_not_expired.count() == 1
    assert funds_ran_out_not_expired.first() == funding3
    assert funding2 not in funds_ran_out_not_expired
    assert funding4 not in funds_ran_out_not_expired

    # Check funding expired but has budget
    assert funding2 in funding_expired_budget_left
    assert funding4 in funding_expired_budget_left
    assert funding1 not in funding_expired_budget_left
    assert funding3 not in funding_expired_budget_left


@pytest.mark.django_db
def test_get_projects_with_charges_exceeding_budget(user, project):
    """Test get_projects_with_charges_exceeding_budget function."""
    from main.models import Funding, TimeEntry
    from main.utils import get_projects_with_charges_exceeding_budget

    date = datetime(2025, 7, 10)
    current_month_start = datetime(date.year, date.month, 1)

    # Create time entry in the last month
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=16)

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    # Create funding for the project
    Funding.objects.create(
        project=project,
        budget=100,
        source="Test Source",
        daily_rate=400,
        expiry_date=current_month_start + timedelta(days=30),  # Not expired
    )

    result = get_projects_with_charges_exceeding_budget(date=date)

    # Check if the project is in the result
    assert len(result) == 1
    assert result[0][0] == project
    assert result[0][1] > 100  # Total charges should exceed the budget
    assert result[0][2] == 100


@pytest.mark.django_db
def test_project_within_budget(user, project):
    """Test if a project is within budget."""
    from main.models import Funding, TimeEntry
    from main.utils import get_projects_with_charges_exceeding_budget

    date = datetime(2025, 7, 10)
    current_month_start = datetime(date.year, date.month, 1)

    # Create time entry in the last month
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=14)

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    # Create funding for the project
    Funding.objects.create(
        project=project,
        budget=1000,
        source="Test Source",
        daily_rate=400,
        expiry_date=current_month_start + timedelta(days=30),  # Not expired
    )

    result = get_projects_with_charges_exceeding_budget(date=date)

    # Check if the project is not in the result
    assert len(result) == 0


@pytest.mark.django_db
def test_project_charges_exceeding_budget(user, project):
    """Test if a project charges exceed the budget."""
    from main.models import Funding, TimeEntry
    from main.utils import get_projects_with_charges_exceeding_budget

    date = datetime(2025, 7, 10)
    current_month_start = datetime(date.year, date.month, 1)

    # Create time entry in the last month
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=21)

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    # Create funding for the project
    Funding.objects.create(
        project=project,
        budget=1000,
        source="Test Source",
        daily_rate=400,
        expiry_date=current_month_start + timedelta(days=30),  # Not expired
    )

    result = get_projects_with_charges_exceeding_budget(date=date)

    # Check if the project is in the result
    assert len(result) == 1
    assert result[0][0] == project
    assert result[0][1] > 1000
