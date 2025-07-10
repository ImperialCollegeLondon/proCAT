"""Task definitions for project notifications using Huey."""

import os
from datetime import datetime, timedelta

from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

from main.Clockify.api_interface import ClockifyAPI
from main.models import Project, TimeEntry, User
from main.notify import email_user
from main.utils import get_current_and_last_month, get_logged_hours

_template = """
Dear {project_leader},

The project {project_name} has {threshold}% {threshold_type} left ({value} {unit}).
Please check the project status and update your time spent on it.

Best regards,
ProCAT
"""


def notify_left_threshold_logic(
    email: str,
    lead: str,
    project_name: str,
    threshold_type: str,
    threshold: int,
    value: int,
) -> None:
    """Logic for notifying the lead about project status."""
    if threshold_type not in ("effort", "weeks"):
        raise ValueError("Invalid threshold type provided.")
    unit = "days" if threshold_type == "effort" else "weeks"
    subject = f"[Project Status Update] {project_name}"
    message = _template.format(
        project_leader=lead,
        project_name=project_name,
        threshold=threshold,
        threshold_type=threshold_type.rsplit("_")[0],
        value=value,
        unit=unit,
    )

    email_user(subject, email, message)


@task()
def notify_left_threshold(
    email: str,
    lead: str,
    project_name: str,
    threshold_type: str,
    threshold: int,
    value: int,
) -> None:
    """Huey task wrapper that calls the core notify logic."""
    notify_left_threshold_logic(
        email, lead, project_name, threshold_type, threshold, value
    )


# Runs every day at 10:00 AM
@db_periodic_task(crontab(hour=10, minute=0))
def daily_project_status_check() -> None:
    """Daily task to check project statuses and notify leads."""
    from .models import Project

    projects = Project.objects.filter(status="Active")
    for project in projects:
        project.check_and_notify_status()


_template_time_logged = """
Dear {user},

This is your monthly summary of project work. In {last_month_name} you have logged:

{project_work_summary}

You have invested on project work approximately {percentage}% of your time.

If you have more time to log for {last_month_name}, please do so by the 10th of
{current_month_name} in [Clockify](https://clockify.me/).

Best wishes,
ProCAT
"""


def notify_monthly_time_logged_logic(
    last_month_start: datetime,
    last_month_name: str,
    current_month_start: datetime,
    current_month_name: str,
) -> None:
    """Logic to notify users about their monthly time logged."""
    from .models import TimeEntry, User

    avg_work_days_per_month = 220 / 12  # Approximately 18.33 days per month

    time_entries = TimeEntry.objects.filter(
        start_time__gte=last_month_start, end_time__lt=current_month_start
    )

    if not time_entries.exists():
        return  # No entries to process

    users = User.objects.filter(timeentry__in=time_entries).distinct()

    for user in users:
        total_hours, project_work_summary = get_logged_hours(
            time_entries.filter(user=user)
        )

        total_days = total_hours / 7  # Assuming 7 hours/workday
        percentage = round((total_days * 100) / avg_work_days_per_month, 1)

        message = _template_time_logged.format(
            user=user.get_full_name(),
            last_month_name=last_month_name,
            project_work_summary=project_work_summary,
            percentage=percentage,
            current_month_name=current_month_name,
        )

        subject = f"Your Project Time Logged Summary for {last_month_name}"

        email_user(
            subject=subject,
            message=message,
            email=user.email,
        )


# Runs on the 3rd day of every month at 10:00 AM
@db_periodic_task(crontab(day=3, hour=10))
def notify_monthly_time_logged_summary() -> None:
    """Monthly task to notify users about their time logged."""
    last_month_start, last_month_name, current_month_start, current_month_name = (
        get_current_and_last_month()
    )

    notify_monthly_time_logged_logic(
        last_month_start,
        last_month_name,
        current_month_start,
        current_month_name,
    )


@task()
def sync_clockify_time_entries() -> None:
    """Task to sync time entries from Clockify API to TimeEntry model."""
    api_key = os.getenv("CLOCKIFY_API_KEY")
    if not api_key:
        print("Clockify API key not found in environment variables")
        return

    days_back = 30
    api = ClockifyAPI(api_key)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days_back)

    project_ids = list(
        Project.objects.exclude(clockify_id="").values_list("clockify_id", flat=True)
    )

    total_entries_synced = 0
    total_entries_skipped = 0

    for project_id in project_ids:
        try:
            print(f"Processing project ID: {project_id}")
            payload = {
                "dateRangeStart": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
                "dateRangeEnd": end_date.strftime("%Y-%m-%dT23:59:59.000Z"),
                "detailedFilter": {"page": 1, "pageSize": 200},
                "projects": {"contains": "CONTAINS", "ids": [project_id]},
            }

            response = api.get_time_entries(payload)
            entries = response.get("timeentries", [])
            if not isinstance(entries, list):
                entries = []

            project_entries_synced = 0
            project_entries_skipped = 0

            for entry in entries:
                entry_id = entry.get("id") or entry.get("_id")
                project_id = entry.get("projectId")
                user_email = entry.get("userEmail")
                time_interval = entry.get("timeInterval", {})
                start = time_interval.get("start")
                end = time_interval.get("end")

                if not (project_id and user_email and start and end):
                    continue

                try:
                    project = Project.objects.get(clockify_id=project_id)
                except Project.DoesNotExist:
                    print(f"Project with clockify_id {project_id} not found.")
                    continue

                try:
                    user = User.objects.get(email=user_email)
                except User.DoesNotExist:
                    print(f"User with email {user_email} not found.")
                    continue

                start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))

                existing_entry = TimeEntry.objects.filter(
                    user=user,
                    project=project,
                    start_time=start_time,
                    end_time=end_time,
                ).exists()

                if existing_entry:
                    project_entries_skipped += 1
                    continue

                TimeEntry.objects.create(
                    user=user,
                    project=project,
                    start_time=start_time,
                    end_time=end_time,
                    clockify_id=entry_id,
                )
                project_entries_synced += 1

            total_entries_synced += project_entries_synced
            total_entries_skipped += project_entries_skipped

        except Exception as e:
            print(f"Error syncing time entries for project {project_id}: {e}")
