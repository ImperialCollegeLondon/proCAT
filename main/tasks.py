"""Task definitions for project notifications using Huey."""

from .huey import huey
from .notify import email_lead_project_status


def notify_left_threshold_logic(
    email: str, project_name: str, threshold_type: str, threshold: int
) -> None:
    """Logic for notifying the lead about project status."""
    if threshold_type == "effort_left":
        message = (
            f"The project {project_name} has {threshold}% effort left. "
            "Please check the project status and update your time spent on it."
        )
    elif threshold_type == "weeks_left":
        message = (
            f"The project {project_name} has {threshold}% weeks left. "
            "Please check the project status and update your time spent on it."
        )
    else:
        raise ValueError("Invalid threshold type provided.")

    email_lead_project_status(email, project_name, message)


@huey.task()
def notify_left_threshold(
    email: str, project_name: str, threshold_type: str, threshold: int
) -> None:
    """Huey task wrapper that calls the core notify logic."""
    notify_left_threshold_logic(email, project_name, threshold_type, threshold)
