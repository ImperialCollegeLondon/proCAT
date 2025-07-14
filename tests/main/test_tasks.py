"""Tests for the tasks module."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from main.tasks import (
    email_monthly_charges_report_logic,
    notify_funding_status_logic,
    notify_left_threshold_logic,
    notify_monthly_charges_exceeding_budget_logic,
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
def test_funding_expired_but_has_budget(funding, project):
    """Test that funding expired but has budget."""
    # Create a funding object with expired date but still has budget
    funding.expiry_date = datetime.now().date() - timedelta(days=1)
    funding.budget = 1000
    funding.save()
    funding.refresh_from_db()
    assert funding.expiry_date < datetime.now().date()
    assert funding.budget > 0

    expected_subject = f"[Funding Expired] {project.name}"

    expected_message = (
        f"\nDear {funding.project.lead.get_full_name()},\n\n"
        f"The project {project.name} has expired, but there is still unspent "
        f"funds of\n£{funding.budget} available.\n\n"
        f"Please check the funding status and take necessary actions.\n\n"
        f"Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_user_and_cc_admin") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            subject=expected_subject,
            email=funding.project.lead.email,
            admin_email=[],
            message=expected_message,
        )


@pytest.mark.django_db
def test_funding_ran_out_not_expired(funding, project):
    """Test that funding ran out but not expired."""
    # Create a funding object with not expired date but budget ran out
    funding.expiry_date = datetime.now().date() + timedelta(days=30)
    funding.budget = -1000
    funding.save()
    funding.refresh_from_db()
    assert funding.expiry_date > datetime.now().date()
    assert funding.budget < 0

    expected_subject = f"[Funding Update] {project.name}"

    expected_message = (
        f"\nDear {funding.project.lead.get_full_name()},\n\n"
        f"The funding {funding.activity} for project {project.name} has run out.\n\n"
        f"If the project has been completed, no further action is needed. "
        f"Otherwise,\nplease check the funding status and take necessary actions.\n\n"
        f"Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_user_and_cc_admin") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            subject=expected_subject,
            email=funding.project.lead.email,
            admin_email=[],
            message=expected_message,
        )


@pytest.mark.django_db
def test_email_monthly_charges_report():
    """Tests that the monthly charges report is generated and emailed."""
    from main import models, report

    month, month_name, year = 6, "June", 2025
    admin_user = models.User.objects.create(
        first_name="admin",
        last_name="user",
        email="admin.user@mail.com",
        password="1234",
        username="admin_user",
        is_superuser=True,
    )

    # Create attachment with empty charges row
    expected_subject = f"Charges report for {month_name}"
    expected_attachment = report.create_charges_report_for_attachment(month, year)
    expected_fname = f"charges_report_{month}-{year}.csv"
    expected_message = (
        f"\nDear {admin_user.get_full_name()},\n\n"
        f"Please find attached the charges report for the last month: {month_name}.\n\n"
        "Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_attachment") as mock_email_attachment:
        email_monthly_charges_report_logic(month, year, month_name)
        mock_email_attachment.assert_called_with(
            expected_subject,
            [admin_user.email],
            expected_message,
            expected_fname,
            expected_attachment,
            "text/csv",
        )


@pytest.mark.django_db
def test_monthly_charges_not_exceeding_budget(funding, project):
    """Test that no email is sent if monthly charges do not exceed budget."""
    from main.models import TimeEntry

    # Create a time entry with charges within budget
    TimeEntry.objects.create(
        user=funding.project.lead,
        project=project,
        start_time=datetime(2025, 6, 1, 9, 0),
        end_time=datetime(2025, 6, 1, 16, 0),  # 7 hours, so equal to 1 work day
    )

    with patch("main.tasks.email_user_and_cc_admin") as mock_email_user:
        notify_monthly_charges_exceeding_budget_logic()
        # No email sent since available budget = 1000 > charges = 389 for 1 day work
        mock_email_user.assert_not_called()


@pytest.mark.django_db
def test_monthly_charges_exceeding_budget(funding, project):
    """Test that an email is sent if monthly charges exceed budget."""
    from main.models import TimeEntry

    # Create a time entry with charges exceeding budget
    TimeEntry.objects.create(
        user=funding.project.lead,
        project=project,
        start_time=datetime(2025, 6, 1, 9, 0),
        end_time=datetime(2025, 6, 1, 16, 0),  # 7 hours, so equal to 1 work day
    )

    funding.budget = Decimal("100")
    funding.save()

    expected_subject = f"[Monthly Charge Exceeding Budget] {project.name}"
    expected_message = (
        f"\nDear {funding.project.lead.get_full_name()},\n\n"
        f"The total charges for project {project.name} in the last month have "
        f"exceeded\nthe budget.\n\n"
        f"Total charges: £389.000\n"
        f"Budget: £{funding.budget}\n\n"
        f"Please review the project budget and take necessary actions.\n\n"
        f"Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_user_and_cc_admin") as mock_email_func:
        notify_monthly_charges_exceeding_budget_logic()
        # Email sent since available budget = 100 < charges = 389 for 1 day work
        mock_email_func.assert_called_once_with(
            subject=expected_subject,
            email=funding.project.lead.email,
            admin_email=[],
            message=expected_message,
        )
