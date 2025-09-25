"""Tests for the tasks module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from main.models import TimeEntry
from main.tasks import (
    email_monthly_charges_report_logic,
    notify_funding_status_logic,
    notify_left_threshold_logic,
    notify_monthly_days_used_exceeding_days_left_logic,
    notify_monthly_time_logged_logic,
    sync_clockify_time_entries,
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
        f"funds of\n£{funding.funding_left} available (£{funding.budget} total).\n\n"
        f"Please check the funding status and take necessary actions.\n\n"
        f"Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_user_and_cc_head") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            subject=expected_subject,
            email=funding.project.lead.email,
            head_email=[],
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

    with patch("main.tasks.email_user_and_cc_head") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            subject=expected_subject,
            email=funding.project.lead.email,
            head_email=[],
            message=expected_message,
        )


@pytest.mark.django_db
def test_email_monthly_charges_report():
    """Tests that the monthly charges report is generated and emailed."""
    from main import models, report

    month, month_name, year = 6, "June", 2025
    head_user = models.User.objects.create(
        first_name="head",
        last_name="user",
        email="head.user@mail.com",
        password="1234",
        username="head_user",
        is_superuser=True,
    )
    group = Group.objects.get(name="HoRSE")
    head_user.groups.add(group)

    # Create attachment with empty charges row
    expected_subject = f"Charges report for {month_name}/{year}"
    expected_attachment = report.create_charges_report_for_attachment(month, year)
    expected_fname = f"charges_report_{month}-{year}.csv"
    expected_message = (
        f"\nDear Head of the RSE team,\n\n"
        f"Please find attached the charges report for the last month: {month_name}/"
        f"{year}.\n\n"
        "Best regards,\nProCAT\n"
    )

    with patch("main.tasks.email_attachment") as mock_email_attachment:
        email_monthly_charges_report_logic(month, year, month_name)
        mock_email_attachment.assert_called_with(
            expected_subject,
            [head_user.email],
            expected_message,
            expected_fname,
            expected_attachment,
            "text/csv",
        )


@pytest.mark.django_db
class TestSyncClockifyTimeEntries:
    """Tests for the sync_clockify_time_entries function."""

    @patch("main.tasks.settings")
    @patch("main.tasks.ClockifyAPI")
    @patch("main.tasks.timezone.now")
    def test_sync_creates_new_entry(
        self, mock_now, mock_clockify_api, mock_settings, user, funding
    ):
        """Test that a new time entry from the API is created in the database."""
        mock_now.return_value = timezone.make_aware(datetime(2025, 7, 16, 10, 0, 0))
        mock_settings.CLOCKIFY_API_KEY = "fake_key"
        mock_settings.CLOCKIFY_WORKSPACE_ID = "fake_workspace"
        project = funding.project
        project.clockify_id = "proj_1"
        project.status = "Active"
        project.save()

        mock_api_instance = mock_clockify_api.return_value
        mock_api_instance.get_time_entries.return_value = {
            "timeentries": [
                {
                    "id": "entry_new",
                    "projectId": project.clockify_id,
                    "userEmail": user.email,
                    "timeInterval": {
                        "start": "2025-07-15T10:00:00Z",
                        "end": "2025-07-15T11:00:00Z",
                    },
                }
            ]
        }

        assert TimeEntry.objects.count() == 0
        sync_clockify_time_entries()

        assert TimeEntry.objects.count() == 1
        new_entry = TimeEntry.objects.first()
        assert new_entry.clockify_id == "entry_new"
        assert new_entry.user == user
        assert new_entry.project == project

    @patch("main.tasks.settings")
    @patch("main.tasks.ClockifyAPI")
    def test_no_api_key(self, mock_clockify_api, mock_settings, caplog):
        """Test that the function exits gracefully if no API key is set."""
        mock_settings.CLOCKIFY_API_KEY = ""
        sync_clockify_time_entries()
        mock_clockify_api.assert_not_called()
        assert "Clockify API key not found" in caplog.text

    @patch("main.tasks.settings")
    @patch("main.tasks.ClockifyAPI")
    def test_api_call_exception(
        self, mock_clockify_api, mock_settings, funding, caplog
    ):
        """Test that an error is logged if the API call fails."""
        mock_settings.CLOCKIFY_API_KEY = "fake_key"
        mock_settings.CLOCKIFY_WORKSPACE_ID = "fake_workspace"
        project = funding.project
        project.clockify_id = "proj_1"
        project.status = "Active"
        project.save()

        mock_api_instance = mock_clockify_api.return_value
        mock_api_instance.get_time_entries.side_effect = Exception("API is down")

        sync_clockify_time_entries()

        assert "Error fetching time entries" in caplog.text
        assert "API is down" in caplog.text
        assert TimeEntry.objects.count() == 0

    @patch("main.tasks.settings")
    @patch("main.tasks.ClockifyAPI")
    def test_skips_incomplete_entry(
        self, mock_clockify_api, mock_settings, user, funding, caplog
    ):
        """Test that entries with missing data are skipped."""
        mock_settings.CLOCKIFY_API_KEY = "fake_key"
        mock_settings.CLOCKIFY_WORKSPACE_ID = "fake_workspace"
        project = funding.project
        project.clockify_id = "proj_1"
        project.status = "Active"
        project.save()

        mock_api_instance = mock_clockify_api.return_value
        mock_api_instance.get_time_entries.return_value = {
            "timeentries": [{"id": "incomplete_entry"}]
        }

        sync_clockify_time_entries()

        assert "Skipping incomplete entry" in caplog.text
        assert TimeEntry.objects.count() == 0

    @patch("main.tasks.settings")
    @patch("main.tasks.ClockifyAPI")
    def test_skips_entry_if_user_not_found(
        self, mock_clockify_api, mock_settings, funding, caplog
    ):
        """Test that entries are skipped if the user does not exist in the database."""
        mock_settings.CLOCKIFY_API_KEY = "fake_key"
        mock_settings.CLOCKIFY_WORKSPACE_ID = "fake_workspace"
        project = funding.project
        project.clockify_id = "proj_1"
        project.status = "Active"
        project.save()

        mock_api_instance = mock_clockify_api.return_value
        mock_api_instance.get_time_entries.return_value = {
            "timeentries": [
                {
                    "id": "entry_no_user",
                    "projectId": project.clockify_id,
                    "userEmail": "non.existent.user@example.com",
                    "timeInterval": {
                        "start": "2025-07-15T12:00:00Z",
                        "end": "2025-07-15T13:00:00Z",
                    },
                }
            ]
        }

        sync_clockify_time_entries()

        assert "User non.existent.user@example.com not found" in caplog.text
        assert TimeEntry.objects.count() == 0


@pytest.mark.django_db
def test_monthly_days_used_not_exceeding_days_left(user, project, funding):
    """Test that no email is sent if days used do not exceed days left."""
    from main.models import TimeEntry

    funding.project = project
    funding.save()
    project.status = "Active"
    project.save()

    # Create a time entry within the allowed days
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=14)  # So days_used is only 2.0 days

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    with patch("main.tasks.email_user_and_cc_head") as mock_email_func:
        notify_monthly_days_used_exceeding_days_left_logic(date=datetime(2025, 7, 10))
        mock_email_func.assert_not_called()


@pytest.mark.django_db
def test_monthly_days_used_exceeding_days_left(user, project, funding):
    """Test that an email is sent when days used exceed days left."""
    from main.models import TimeEntry

    funding.project = project  # 26 days total effort
    funding.save()
    project.status = "Active"
    project.save()

    # Create a time entry that exceeds the days left
    start_time = datetime(2025, 6, 1, 11, 0)
    end_time = start_time + timedelta(hours=203)  # So days_used is 29.0 days

    TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=start_time,
        end_time=end_time,
    )

    with patch("main.tasks.email_user_and_cc_head") as mock_email_func:
        notify_monthly_days_used_exceeding_days_left_logic(date=datetime(2025, 7, 10))

        mock_email_func.assert_called_once_with(
            subject=f"[Monthly Days Used Exceed Days Left] {project.name}",
            message=(
                "\nDear test user,\n\n"
                f"The total days used for project {project.name} has exceeded "
                "the total budget.\n\n"
                "Days left: -3.3\n"
                "Total days for project: 25.7\n\n"
                "Please review the project budget and take necessary actions.\n\n"
                "Best regards,\nProCAT\n"
            ),
            email=project.lead.email if project.lead else user.email,
            head_email=[],
        )
