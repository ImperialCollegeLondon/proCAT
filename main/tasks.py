"""Task definitions for project notifications using Huey."""

from datetime import datetime

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

from .notify import email_lead

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

    email_lead(subject, email, message)


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
Dear {project_leader},

This is your monthly summary of project work. In {last_month_name} you have logged:

{project_work_summary}

You have invested on project work {percentage}% of your time.

If you have more time to log for {last_month_name}, please do so by the 10th of
{current_month_name} in [Clockify](https://clockify.me/).

Best wishes,
ProCAT
"""


# Runs on the 3rd day of every month at 10:00 AM
@db_periodic_task(crontab(day=3, hour=10))
def notify_monthly_time_logged_summary() -> None:
    """Notify users about their monthly time logged."""
    from .models import TimeEntry, User

    avg_work_days_per_month = 220 / 12  # Approximately 18.33 days per month

    today = datetime.today()

    last_month_start = datetime(year=today.year, month=today.month - 1, day=1)
    current_month_start = datetime(year=today.year, month=today.month, day=1)

    time_entries = TimeEntry.objects.filter(
        start_time__gte=last_month_start, end_time__lt=current_month_start
    )

    if not time_entries.exists():
        return  # No entries to process

    users = User.objects.filter(timeentry__in=time_entries).distinct()

    for user in users:
        user_entries = time_entries.filter(user=user)

        project_hours: dict[str, float] = {}
        total_hours = 0.0

        for entry in user_entries:
            project_name = entry.project.name
            hours = (entry.end_time - entry.start_time).total_seconds() / 3600
            total_hours += hours
            project_hours.setdefault(project_name, 0.0)
            project_hours[project_name] += hours

        if total_hours == 0:
            continue  # No hours logged for this user

        project_work_summary = "\n".join(
            [
                f"{project}: {round(hours / 8, 1)} days"  # Assuming 8 hours/workday
                for project, hours in project_hours.items()
            ]
        )

        total_days = total_hours / 8  # Assuming 8 hours/workday
        percentage = round((total_days * 100) / avg_work_days_per_month, 1)

        last_month_name = last_month_start.strftime("%B")
        current_month_name = current_month_start.strftime("%B")

        message = _template_time_logged.format(
            project_leader=user.get_full_name(),
            last_month_name=last_month_name,
            project_summary=project_work_summary,
            percentage=percentage,
            current_month_name=current_month_name,
        )

        subject = f"Your Project Time Logged Summary for {last_month_name}"

        email_lead(
            subject=subject,
            message=message,
            email=user.email,
        )
