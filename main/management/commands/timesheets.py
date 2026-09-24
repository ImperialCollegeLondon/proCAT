"""Timesheets management command."""

from datetime import timedelta
from pprint import pprint

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.Kimai.api_interface import KimaiAPI


class Command(BaseCommand):
    """Management command to retrieve timesheets."""

    help = "Displays timesheets related to the selected project and time range."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        """Arguments to be parsed from the input."""
        parser.add_argument(
            "-t", "--time", type=int, help="Time entries logged in last TIME days"
        )
        parser.add_argument(
            "-p", "--project", type=int, help="PROJECT id to get time entries for."
        )

    def handle(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Actual function to be executed."""
        days = kwargs.get("time")
        if not days:
            raise ValueError("A integer number of days must be provided.")
        project_id = kwargs.get("project")
        if not project_id:
            raise ValueError("A project ID number must be provided.")

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        kimai = KimaiAPI(settings.KIMAI_API_TOKEN, settings.KIMAI_BASE_URL)
        entries = kimai.get_time_entries(start_date, end_date, project_id)

        pprint(entries)
