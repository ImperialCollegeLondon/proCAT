"""Tests for the Clockify API interface."""

import json
from unittest.mock import Mock, patch

import pytest
import requests


def test_process_entry(kimai_response, kimai_response_invalid):
    """Test the _process_entry function."""
    from main.Kimai.api_interface import _process_entry

    entry = kimai_response[0]
    valid = _process_entry(entry)
    assert valid["entry_id"] == entry.get("id")
    assert valid["project_id"] == entry.get("project", {}).get("id")
    assert valid["user_email"] == entry.get("user", {}).get("email")
    assert valid["start"] == entry.get("begin")
    assert valid["end"] == entry.get("end")

    with pytest.raises(ValueError, match=r"Error processing time entry for project"):
        entry = kimai_response_invalid[0]
        _process_entry(entry)


class TestKimaiAPI:
    """Test suite for the KimaiAPI class."""

    def test_init(self):
        """Test the initialization of KimaiAPI."""
        from main.Kimai.api_interface import KimaiAPI

        for key, url in (("", ""), ("api", ""), ("", "url")):
            with pytest.raises(
                ValueError, match=r"Missing Kimai API key, base_url or both."
            ):
                KimaiAPI(key, url)

        key = "1234"
        url = "http://some.url"
        client = KimaiAPI(key, url)
        assert client.base_url == url
        assert key in client.headers["Authorization"]

    @patch("main.Kimai.api_interface.requests.request")
    def test_get_time_entries_success(self, mock_request, kimai_response):
        """Test successful API call to get time entries."""
        from datetime import datetime

        from main.Kimai.api_interface import KimaiAPI

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = kimai_response
        mock_request.return_value = mock_response

        start_date = datetime.fromisoformat("2026-08-26T14:00:00+0100")
        end_date = datetime.fromisoformat("2026-08-27T13:00:00+0100")
        client = KimaiAPI("1234", "http://some.url")

        result = client.get_time_entries(start_date, end_date, 42)
        assert len(result) == 2

    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_http_error(self, mock_request):
        """Test API call with HTTP error response."""
        from datetime import datetime

        from main.Kimai.api_interface import KimaiAPI

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
        mock_request.return_value = mock_response

        start_date = datetime.fromisoformat("2026-08-26T14:00:00+0100")
        end_date = datetime.fromisoformat("2026-08-27T13:00:00+0100")
        client = KimaiAPI("1234", "http://some.url")

        with pytest.raises(requests.HTTPError, match=r"Unauthorized"):
            client.get_time_entries(start_date, end_date, 42)

        mock_response.raise_for_status.assert_called_once()

    @patch("main.Kimai.api_interface.requests.request")
    def test_get_time_entries_processing_error(
        self, mock_request, kimai_response_invalid, caplog
    ):
        """Test successful API call to get time entries."""
        from datetime import datetime

        from main.Kimai.api_interface import KimaiAPI

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = kimai_response_invalid
        mock_request.return_value = mock_response

        start_date = datetime.fromisoformat("2026-08-26T14:00:00+0100")
        end_date = datetime.fromisoformat("2026-08-27T13:00:00+0100")
        client = KimaiAPI("1234", "http://some.url")

        result = client.get_time_entries(start_date, end_date, 42)
        assert len(result) == 0
        assert caplog.records[-1].levelname == "ERROR"
        msg = "There was a problem processing time entries for project 42"
        assert msg in caplog.records[-1].message


class TestClockifyAPI:
    """Test suite for the ClockifyAPI class."""

    def test_init(self):
        """Test the initialization of ClockifyAPI."""
        from main.Clockify.api_interface import ClockifyAPI

        api_key = "test_api_key"
        workspace_id = "test_workspace_id"
        api = ClockifyAPI(api_key, workspace_id)

        assert api.api_key == api_key
        assert api.base_url == "https://api.clockify.me/api"
        assert api.reports_base_url == "https://reports.api.clockify.me/v1"
        assert api.headers == {"Content-Type": "application/json", "X-Api-Key": api_key}

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

        api = ClockifyAPI("test_api_key", "test_workspace_id")
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

    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_http_error(self, mock_request):
        """Test API call with HTTP error response."""
        from main.Clockify.api_interface import ClockifyAPI

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
        mock_request.return_value = mock_response

        api = ClockifyAPI("invalid_api_key", "test_workspace_id")
        payload = {"dateRangeStart": "2024-09-01T00:00:00.000Z"}

        with pytest.raises(requests.HTTPError, match=r"Unauthorized"):
            api.get_time_entries(payload)

        mock_response.raise_for_status.assert_called_once()

    @patch("main.Clockify.api_interface.requests.request")
    def test_get_time_entries_empty_payload(self, mock_request):
        """Test API call with empty payload."""
        from main.Clockify.api_interface import ClockifyAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"timeentries": []}
        mock_request.return_value = mock_response

        api = ClockifyAPI("test_api_key", "test_workspace_id")
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
