"""Task definitions for project notifications using Huey."""

import datetime

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

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


_template_funds_ran_out_but_not_expired = """
Dear {project_leader},

The funding for project {project_name} has run out but the project has
not yet expired.

Please check the funding status and take necessary actions.

Best regards,
ProCAT
"""

_template_funding_expired_but_has_budget = """
Dear {project_leader},

The project {project_name} has expired, but there is still unspent funds of
£{budget} available.

Please check the funding status and take necessary actions.

Best regards,
ProCAT
"""


def notify_funding_status_logic(
    date: datetime.date | None = None,
) -> None:
    """Logic for notifying the lead about funding status."""
    from .models import Funding

    if date is None:
        date = datetime.date.today()

    funds_ran_out_but_not_expired = Funding.objects.filter(
        expiry_date__gt=date, budget__lt=0
    )
    funding_expired_but_has_budget = Funding.objects.filter(
        expiry_date__lt=date, budget__gt=0
    )

    if funds_ran_out_but_not_expired.exists():
        for funding in funds_ran_out_but_not_expired:
            message = _template_funds_ran_out_but_not_expired.format(
                project_leader=funding.project.lead.get_full_name(),
                project_name=funding.project.name,
            )
            email_lead_project_status(
                funding.project.lead.email, funding.project.name, message
            )

    if funding_expired_but_has_budget.exists():
        for funding in funding_expired_but_has_budget:
            message = _template_funding_expired_but_has_budget.format(
                project_leader=funding.project.lead.get_full_name(),
                project_name=funding.project.name,
                budget=funding.budget,
            )
            email_lead_project_status(
                funding.project.lead.email, funding.project.name, message
            )


# Runs every day at 11:00 AM
@db_periodic_task(crontab(hour=11, minute=0))
def notify_funding_status() -> None:
    """Daily task to notify about funding status."""
    notify_funding_status_logic()
