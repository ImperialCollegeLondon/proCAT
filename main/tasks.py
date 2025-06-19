"""Task definitions for project notifications using Huey."""

from huey import crontab

from .huey import huey
from .notify import email_lead_project_status

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
    message = _template.format(
        project_leader=lead,
        project_name=project_name,
        threshold=threshold,
        threshold_type=threshold_type.rsplit("_")[0],
        value=value,
        unit=unit,
    )

    email_lead_project_status(email, project_name, message)


@huey.task()
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
@huey.periodic_task(crontab(hour=10, minute=0))
def daily_project_status_check() -> None:
    """Daily task to check project statuses and notify leads."""
    from .models import Project

    projects = Project.objects.filter(status="Active")
    for project in projects:
        project.check_and_notify_status()
