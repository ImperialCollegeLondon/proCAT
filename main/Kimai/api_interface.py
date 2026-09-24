"""Kimai API Interface Module."""

from collections.abc import Mapping
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any

import requests

logger = getLogger(__name__)


class KimaiAPI:
    """A class to interact with the Clockify API for project management."""

    def __init__(self, api_key: str, base_url: str):
        """Initialize the KimaiAPI instance.

        Args:
            api_key: Your personal Kimai API key.
            base_url: The base url of Kimai API.
        """
        if not api_key or not base_url:
            raise ValueError("Missing Kimai API key, base_url or both.")

        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def get_time_entries(  # type: ignore[explicit-any]
        self, start_date: datetime, end_date: datetime, project_id: int
    ) -> list[dict[str, Any]]:
        """Retrieve detailed time entries for a specified workspace using the API.

        Args:
            start_date: First day of the time entries to be retrieved.
            end_date: Last day of the time entries to be retrieved.
            project_id: Kimai id of the project to retrieve time entries for.

        Returns:
            List of dictionaries containing the entry id, project id, user email and
            begin and end date time for the entry.

        Raises:
            HTTPError: If the API request fails.
        """
        url = f"{self.base_url}/timesheets"

        payload: Mapping[str, Any] = {  # type: ignore[explicit-any]
            "begin": start_date.strftime("%Y-%m-%dT00:00:00"),
            "end": end_date.strftime("%Y-%m-%dT23:59:59"),
            "full": 1,
            "billable": 1,
            "size": 500,
            "project": project_id,
            "user": "all",
        }

        response = requests.request(
            "GET", url, headers=self.headers, params=payload, verify=False
        )

        if response.status_code == 200:
            try:
                return [_process_entry(p) for p in response.json()]
            except ValueError as e:
                logger.error(
                    "There was a problem processing time entries for project "
                    f"{project_id}: {e}"
                )
                return []
        else:
            response.raise_for_status()
        return []


def _process_entry(entry: dict[str, Any]) -> dict[str, Any]:  # type: ignore[explicit-any]
    """Process a raw entry from Kimai API and extract the relevant values.

    Args:
        entry: The raw entry to process.

    Raises:
        ValueError if any of the values to extract are None/empty.

    Return:
        A dictionary containing the entry id, project id, user email and
        begin and end date time for the entry.
    """
    processed = dict(
        entry_id=entry.get("id"),
        project_id=entry.get("project", {}).get("id"),
        user_email=entry.get("user", {}).get("email"),
        start=entry.get("begin"),
        end=entry.get("end"),
    )

    is_none = [key for key, value in processed.items() if not value]
    if is_none:
        raise ValueError(f"Error processing time entry for project {entry}.")

    return processed


if __name__ == "__main__":
    import os

    KIMAI_BASE_URL = os.environ.get("KIMAI_BASE_URL", "")
    KIMAI_API_TOKEN = os.environ.get("KIMAI_API_TOKEN", "")
    project_id = 78
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    kimai = KimaiAPI(KIMAI_API_TOKEN, KIMAI_BASE_URL)
    entries = kimai.get_time_entries(start_date, end_date, project_id)

    print(entries)
