"""Tests for the utils module."""

from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import Group


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
def test_create_destroy_horse_group():
    """Roundtrip check of creation and destruction of the HoRSE group."""
    from main import utils

    assert Group.objects.filter(name="HoRSE").exists()
    utils.destroy_HoRSE_group()
    assert not Group.objects.filter(name="HoRSE").exists()
    utils.create_HoRSE_group()
    assert Group.objects.filter(name="HoRSE").exists()


def test_get_head_email(user):
    """Test get_head_email function."""
    from main import utils

    group = Group.objects.get(name="HoRSE")
    email = utils.get_head_email()
    assert email == []

    user.groups.add(group)
    email = utils.get_head_email()
    assert email == [user.email]


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
def test_days_used_within_days_left(user, project):
    """Test if days used within days left."""
    from main.models import Funding, TimeEntry
    from main.utils import get_projects_with_days_used_exceeding_days_left

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

    result = get_projects_with_days_used_exceeding_days_left(date=date)

    # Check if the project is not in the result
    assert len(result) == 0, (
        "Project should not be in the result as days used is within days left"
    )
    assert project.days_left == (2.5, 125.0)


@pytest.mark.django_db
def test_days_used_exceeding_days_left(user, project):
    """Test if days used exceeds days left."""
    from main.models import Funding, TimeEntry
    from main.utils import get_projects_with_days_used_exceeding_days_left

    date = datetime(2025, 7, 10)
    current_month_start = datetime(date.year, date.month, 1)

    # Create time entry in the last month
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=50)

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
    project.status = "Active"
    project.save()

    result = get_projects_with_days_used_exceeding_days_left(date=date)

    # Check if the project is in the result
    assert len(result) == 1, (
        "Project should be in the result as days used exceeds days left"
    )
    project_result, days_used, days_left = result[0]
    assert project_result == project
    assert round(days_used, 1) == 7.1
    assert round(days_left, 1) == 2.5


@pytest.mark.django_db
def test_order_queryset_by_property(project, analysis_code):
    """Test the order_queryset_by_property function."""
    from main import models, utils

    # Create some funding objects
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=datetime.today().date(),
        budget=1000.00,
        daily_rate=100.00,
        id=1,
    )  # 10 days funding

    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=datetime.today().date(),
        budget=2000.00,
        daily_rate=100.00,
        id=2,
    )  # 20 days funding

    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=datetime.today().date(),
        budget=500.00,
        daily_rate=100.00,
        id=3,
    )  # 5 days funding

    # Check Funding is ordered correctly by effort
    qs = models.Funding.objects.all()
    ordered_qs = utils.order_queryset_by_property(qs, "effort", False)
    ordered_ids = list(ordered_qs.values_list("id", flat=True))
    assert ordered_ids == [3, 1, 2]

    # Check reverse order
    reverse_qs = utils.order_queryset_by_property(qs, "effort", True)
    reverse_ids = list(reverse_qs.values_list("id", flat=True))
    assert reverse_ids == [2, 1, 3]


def test_get_calendar_year_dates():
    """Test the get_calendar_year_dates function."""
    from main.utils import get_calendar_year_dates

    today = datetime.now()
    assert get_calendar_year_dates()[0].date() == datetime(today.year, 1, 1).date()
    assert get_calendar_year_dates()[1].date() == datetime(today.year, 12, 31).date()


def test_get_financial_year_dates():
    """Test the get_financial_year_dates function."""
    from main.utils import get_financial_year_dates

    today = datetime.now()

    if today.month > 8:
        assert get_financial_year_dates()[0].date() == datetime(today.year, 8, 1).date()
        assert (
            get_financial_year_dates()[1].date()
            == datetime(today.year + 1, 7, 31).date()
        )
    else:
        assert (
            get_financial_year_dates()[0].date()
            == datetime(today.year - 1, 8, 1).date()
        )
        assert (
            get_financial_year_dates()[1].date() == datetime(today.year, 7, 31).date()
        )
