"""Tests for the tasks module."""

from unittest.mock import patch

import pytest

from main.tasks import notify_left_threshold_logic


@pytest.mark.parametrize(
    "threshold_type, threshold, expected_message",
    [
        (
            "effort_left",
            50,
            "The project TestProject has 50% effort left. "
            "Please check the project status and update your time spent on it.",
        ),
        (
            "weeks_left",
            30,
            "The project TestProject has 30% weeks left. "
            "Please check the project status and update your time spent on it.",
        ),
    ],
)
def test_notify_left_threshold_valid_type(threshold_type, threshold, expected_message):
    """Test notify_left_threshold_logic with valid threshold types."""
    email = "lead@example.com"
    project_name = "TestProject"

    with patch("main.tasks.email_lead_project_status") as mock_email_func:
        notify_left_threshold_logic(email, project_name, threshold_type, threshold)
        mock_email_func.assert_called_once_with(email, project_name, expected_message)


def test_notify_left_threshold_invalid_type():
    """Test notify_left_threshold_logic with invalid threshold type."""
    with pytest.raises(ValueError, match="Invalid threshold type provided."):
        notify_left_threshold_logic(
            "lead@example.com", "TestProject", "invalid_type", 10
        )
