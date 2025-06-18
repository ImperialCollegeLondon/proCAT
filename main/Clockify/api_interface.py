"""Clockify API Interface Module."""

import json
import os

import dict
import requests

WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")


class ClockifyAPI:
    """A class to interact with the Clockify API for project management."""

    def __init__(self, api_key: str):
        """Initialize the ClockifyAPI with the provided API key."""
        self.api_key = api_key
        self.base_url = "https://api.clockify.me/api"
        self.reports_base_url = "https://reports.api.clockify.me/v1"
        self.headers = {"Content-Type": "application/json", "X-Api-Key": self.api_key}

    def get_time_entries(self, payload: dict) -> dict:
        """Retrieve detailed time entries for a specified workspace using the API."""
        url = f"{self.reports_base_url}/workspaces/{WORKSPACE_ID}/reports/detailed"

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
