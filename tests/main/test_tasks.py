"""Tests for the tasks module."""

from unittest.mock import patch

import pytest

from main.tasks import notify_left_threshold_logic


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
