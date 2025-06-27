"""Tests for the tasks module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from main.tasks import notify_funding_status_logic, notify_left_threshold_logic


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

    with patch("main.tasks.email_lead_project_status") as mock_email_func:
        notify_left_threshold_logic(
            email, lead, project_name, threshold_type, threshold, value
        )
        mock_email_func.assert_called_once_with(email, project_name, expected_message)


def test_notify_left_threshold_invalid_type():
    """Test notify_left_threshold_logic with invalid threshold type."""
    with pytest.raises(ValueError, match="Invalid threshold type provided."):
        notify_left_threshold_logic(
            "lead@example.com", "Project Lead", "TestProject", "invalid_type", 10, 3
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

    with patch("main.tasks.email_lead_project_status") as mock_email_func:
        notify_funding_status_logic()
        mock_email_func.assert_called_once_with(
            user.email, project.name, expected_message
        )
