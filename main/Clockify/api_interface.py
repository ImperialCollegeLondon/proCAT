"""Clockify API Interface Module."""

import json
from collections.abc import Collection

import requests


class ClockifyAPI:
    """A class to interact with the Clockify API for project management."""

    def __init__(self, api_key: str, workspace_id: str):
        """Initialize the ClockifyAPI instance.

        Args:
            api_key (str): Your personal Clockify API key.
            workspace_id (str): The ID of the Clockify workspace to interact with.
        """
        self.api_key = api_key
        self.base_url = "https://api.clockify.me/api"
        self.reports_base_url = "https://reports.api.clockify.me/v1"
        self.headers = {"Content-Type": "application/json", "X-Api-Key": self.api_key}
        self.workspace_id = workspace_id

    def get_time_entries(
        self, payload: dict[str, Collection[str]]
    ) -> dict[str, object]:
        """Retrieve detailed time entries for a specified workspace using the API.

        Args:
            payload: A dictionary containing filter parameters for the time entries.

        Example payload:
            {
              "dateRangeStart": "2024-09-01T00:00:00.000Z",
              "dateRangeEnd": "2025-01-01T23:59:59.000Z",
              "detailedFilter": {
                "page": 1,
                "pageSize": 200
              },
              "projects": {
                "contains": "CONTAINS",
                "ids": [
                  "6694bb8babec074beb0731cb"
                ]
              }
            }

        Returns:
            dict: The JSON response from the API containing the time entries data.

        Raises:
            HTTPError: If the API request fails.
        """
        url = f"{self.reports_base_url}/workspaces/{self.workspace_id}/reports/detailed"

        headers = {
            "Accept": "",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        json_payload = json.dumps(payload)

        response = requests.request("POST", url, headers=headers, data=json_payload)

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
        return {}
