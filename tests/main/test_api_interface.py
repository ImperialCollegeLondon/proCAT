"""Tests for the Clockify API interface."""

import json
from unittest.mock import Mock, patch

import pytest
import requests


class TestClockifyAPI:
    """Test suite for the ClockifyAPI class."""

    def test_init(self):
        """Test the initialization of ClockifyAPI."""
        from main.Clockify.api_interface import ClockifyAPI

        api_key = "test_api_key"
        api = ClockifyAPI(api_key)

        assert api.api_key == api_key
        assert api.base_url == "https://api.clockify.me/api"
        assert api.reports_base_url == "https://reports.api.clockify.me/v1"
        assert api.headers == {"Content-Type": "application/json", "X-Api-Key": api_key}

    @patch("main.Clockify.api_interface.WORKSPACE_ID", "test_workspace_id")
    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_success(self, mock_request):
        """Test successful API call to get time entries."""
        from main.Clockify.api_interface import ClockifyAPI

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "timeentries": [
                {
                    "_id": "670763ed716e763b41ba5665",
                    "description": "",
                    "userId": "5e57c79e0121f031bdc4be8d",
                    "timeInterval": {
                        "start": "2024-10-10T06:19:41+01:00",
                        "end": "2024-10-10T07:30:41+01:00",
                        "duration": 4260,
                    },
                    "billable": True,
                    "projectId": "6694bb8babec074beb0731cb",
                }
            ]
        }
        mock_request.return_value = mock_response

        api = ClockifyAPI("test_api_key")
        payload = {
            "dateRangeStart": "2024-09-01T00:00:00.000Z",
            "dateRangeEnd": "2025-01-01T23:59:59.000Z",
            "detailedFilter": {"page": 1, "pageSize": 200},
        }

        result = api.get_time_entries(payload)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert (
            call_args[0][1]
            == "https://reports.api.clockify.me/v1/workspaces/test_workspace_id/reports/detailed"
        )
        assert call_args[1]["headers"]["x-api-key"] == "test_api_key"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

        sent_payload = json.loads(call_args[1]["data"])
        assert sent_payload == payload

        assert result == mock_response.json.return_value
        assert "timeentries" in result
        assert len(result["timeentries"]) == 1

    @patch("main.Clockify.api_interface.WORKSPACE_ID", "test_workspace_id")
    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_http_error(self, mock_request):
        """Test API call with HTTP error response."""
        from main.Clockify.api_interface import ClockifyAPI

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
        mock_request.return_value = mock_response

        api = ClockifyAPI("invalid_api_key")
        payload = {"dateRangeStart": "2024-09-01T00:00:00.000Z"}

        with pytest.raises(requests.HTTPError, match="Unauthorized"):
            api.get_time_entries(payload)

        mock_response.raise_for_status.assert_called_once()

    @patch("main.Clockify.api_interface.WORKSPACE_ID", "test_workspace_id")
    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_empty_payload(self, mock_request):
        """Test API call with empty payload."""
        from main.Clockify.api_interface import ClockifyAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"timeentries": []}
        mock_request.return_value = mock_response

        api = ClockifyAPI("test_api_key")
        payload = {}

        result = api.get_time_entries(payload)

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "test_workspace_id" in call_args[0][1]
        assert call_args[1]["headers"]["x-api-key"] == "test_api_key"

        sent_payload = json.loads(call_args[1]["data"])
        assert sent_payload == {}

        assert result == {"timeentries": []}
