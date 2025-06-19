"""Task definitions for project notifications using Huey."""

from .huey import huey
from .notify import email_lead_project_status


def notify_left_threshold_logic(
    email: str, project_name: str, threshold_type: str, threshold: int
) -> None:
    """Logic for notifying the lead about project status."""
    if threshold_type not in ("effort", "weeks_left"):
        raise ValueError("Invalid threshold type provided.")
    unit = "days" if threshold_type == "effort" else "weeks"
    message = _template.format(
                  project_leader=project_leader,
                  project_name=project_name,
                  threshold=threshold,
                  threshold_type=threshold_type.rsplit("_")[0],
                  value=value,
                  unit=unit
              )

    email_lead_project_status(email, project_name, message)


@huey.task()
def notify_left_threshold(
    email: str, project_name: str, threshold_type: str, threshold: int
) -> None:
    """Huey task wrapper that calls the core notify logic."""
    notify_left_threshold_logic(email, project_name, threshold_type, threshold)
