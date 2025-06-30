"""Tests for the tasks module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from main.tasks import (
    notify_funding_status_logic,
    notify_left_threshold_logic,
    notify_monthly_time_logged_logic,
)


@pytest.mark.parametrize(
    "threshold_type, threshold, value, expected_message",
    [
        (
            "effort",
            50,
            10,
            "\nDear Project Lead,\n\n"
            "The project TestProject has 50% effort left (10 days)."
            "\nPlease check the project status and update your time spent on it."
            "\n\nBest regards,\nProCAT\n",
        ),
        (
            "weeks",
            30,
            4,
            "\nDear Project Lead,\n\n"
            "The project TestProject has 30% weeks left (4 weeks)."
            "\nPlease check the project status and update your time spent on it."
            "\n\nBest regards,\nProCAT\n",
        ),
    ],
)
def test_notify_left_threshold_valid_type(
    threshold_type, threshold, value, expected_message
):
    """Test notify_left_threshold_logic with valid threshold types."""
    email = "lead@example.com"
    lead = "Project Lead"
    project_name = "TestProject"
    subject = f"[Project Status Update] {project_name}"

    with patch("main.tasks.email_user") as mock_email_func:
        notify_left_threshold_logic(
            email, lead, project_name, threshold_type, threshold, value
        )
        mock_email_func.assert_called_once_with(subject, email, expected_message)


def test_notify_left_threshold_invalid_type():
    """Test notify_left_threshold_logic with invalid threshold type."""
    with pytest.raises(ValueError, match="Invalid threshold type provided."):
        notify_left_threshold_logic(
            "lead@example.com", "Project Lead", "TestProject", "invalid_type", 10, 3
        )


@pytest.mark.django_db
def test_process_time_logged_summary_sends_email(user, project):
    """Test that the monthly time logged summary sends an email."""
    from main.models import TimeEntry

    # Create a time entry in April 2025
    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 4, 10, 11, 0),
        end_time=datetime(2025, 4, 10, 16, 0),
    )

    last_month_start = datetime(2025, 4, 1)
    current_month_start = datetime(2025, 5, 1)
    last_month_name = "April"
    current_month_name = "May"

    with patch("main.tasks.email_user") as mock_email_user:
        notify_monthly_time_logged_logic(
            last_month_start,
            last_month_name,
            current_month_start,
            current_month_name,
        )

        expected_subject = "Your Project Time Logged Summary for April"
        expected_message = (
            f"\nDear {user.get_full_name()},\n\n"
            f"This is your monthly summary of project work. In April you have "
            f"logged:\n\n"
            f"{project.name}: 0.7 days\n\n"
            f"You have invested on project work approximately 3.9% of your "
            f"time.\n\n"
            f"If you have more time to log for April, please do so by the 10th "
            f"of\n"
            f"May in [Clockify](https://clockify.me/).\n\n"
            f"Best wishes,\nProCAT\n"
        )

        mock_email_user.assert_called_with(
            subject=expected_subject,
            message=expected_message,
            email=user.email,
        )


@pytest.mark.django_db
def test_process_time_logged_summary_no_entries(user):
    """Test that no email is sent if there are no time entries."""
    last_month_start = datetime(2025, 4, 1)
    current_month_start = datetime(2025, 5, 1)
    last_month_name = "April"
    current_month_name = "May"

    with patch("main.tasks.email_user") as mock_email_user:
        notify_monthly_time_logged_logic(
            last_month_start,
            last_month_name,
            current_month_start,
            current_month_name,
        )

        mock_email_user.assert_not_called()


@pytest.mark.django_db
def test_process_time_logged_summary_multiple_projects(user, department):
    """Test that the summary correctly aggregates time across multiple projects."""
    from main.models import Project, TimeEntry

    project1 = Project.objects.create(name="Project 1", department=department)
    project2 = Project.objects.create(name="Project 2", department=department)

    # Create time entries for both projects
    TimeEntry.objects.create(
        user=user,
        project=project1,
        start_time=datetime(2025, 4, 10, 11, 0),
        end_time=datetime(2025, 4, 10, 16, 0),
    )
    TimeEntry.objects.create(
        user=user,
        project=project2,
        start_time=datetime(2025, 4, 11, 9, 0),
        end_time=datetime(2025, 4, 11, 17, 0),
    )

    last_month_start = datetime(2025, 4, 1)
    current_month_start = datetime(2025, 5, 1)
    last_month_name = "April"
    current_month_name = "May"

    with patch("main.tasks.email_user") as mock_email_user:
        notify_monthly_time_logged_logic(
            last_month_start,
            last_month_name,
            current_month_start,
            current_month_name,
        )

        expected_subject = "Your Project Time Logged Summary for April"
        expected_message = (
            f"\nDear {user.get_full_name()},\n\n"
            f"This is your monthly summary of project work. In April you have "
            f"logged:\n\n"
            f"Project 1: 0.7 days\n"
            f"Project 2: 1.1 days\n\n"
            f"You have invested on project work approximately 10.1% of your "
            f"time.\n\n"
            f"If you have more time to log for April, please do so by the 10th "
            f"of\n"
            f"May in [Clockify](https://clockify.me/).\n\n"
            f"Best wishes,\nProCAT\n"
        )

        mock_email_user.assert_called_with(
            subject=expected_subject,
            message=expected_message,
            email=user.email,
        )


@pytest.mark.django_db
def test_funding_expired_but_has_budget(funding, project, user):
    """Test that funding expired but has budget."""
    # Create a funding object with expired date but still has budget
    funding.expiry_date = datetime.now().date() - timedelta(days=1)
    funding.budget = 1000
    funding.save()
    funding.refresh_from_db()
    assert funding.expiry_date < datetime.now().date()
    assert funding.budget > 0

    expected_message = (
        f"\nDear {funding.project.lead.get_full_name()},\n\n"
        f"The project {project.name} has expired, but there is still unspent "
        f"funds of\n£{funding.budget} available.\n\n"
        f"Please check the funding status and take necessary actions.\n\n"
        f"Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_user") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            user.email, project.name, expected_message
        )
