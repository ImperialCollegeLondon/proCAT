"""Task definitions for project notifications using Huey."""

from huey import Huey

from .notify import email_lead_project_status

huey = Huey()


@huey.task()
def notify_left_threshold(
    email: str, project_name: str, threshold_type: str, threshold: int
) -> None:
    """Notify project lead about the project status based on thresholds."""
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
