"""Task definitions for project notifications using Huey."""

import datetime

from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

from .notify import email_attachment, email_user, email_user_and_cc_admin
from .report import create_charges_report_for_attachment
from .utils import (
    get_admin_email,
    get_admin_name,
    get_budget_status,
    get_current_and_last_month,
    get_logged_hours,
    get_projects_with_charges_exceeding_budget,
)

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
    last_month_start: datetime.date,
    last_month_name: str,
    current_month_start: datetime.date,
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


_template_funds_ran_out_but_not_expired = """
Dear {lead},

The funding {activity} for project {project_name} has run out.

If the project has been completed, no further action is needed. Otherwise,
please check the funding status and take necessary actions.

Best regards,
ProCAT
"""

_template_funding_expired_but_has_budget = """
Dear {lead},

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
    funds_ran_out_not_expired, funding_expired_budget_left = get_budget_status(
        date=date
    )

    if funds_ran_out_not_expired.exists():
        for funding in funds_ran_out_not_expired:
            subject = f"[Funding Update] {funding.project.name}"
            admin_email = get_admin_email()
            lead = funding.project.lead
            lead_name = lead.get_full_name() if lead is not None else "Project Leader"
            lead_email = lead.email if lead is not None else ""
            activity = funding.activity if funding.activity else "Funding Activity"
            message = _template_funds_ran_out_but_not_expired.format(
                lead=lead_name,
                project_name=funding.project.name,
                activity=activity,
            )
            email_user_and_cc_admin(
                subject=subject,
                message=message,
                email=lead_email,
                admin_email=admin_email,
            )

    if funding_expired_budget_left.exists():
        for funding in funding_expired_budget_left:
            subject = f"[Funding Expired] {funding.project.name}"
            admin_email = get_admin_email()
            lead = funding.project.lead
            lead_name = lead.get_full_name() if lead is not None else "Project Leader"
            lead_email = lead.email if lead is not None else ""
            message = _template_funding_expired_but_has_budget.format(
                lead=lead_name,
                project_name=funding.project.name,
                budget=funding.budget,
            )
            email_user_and_cc_admin(
                subject=subject,
                message=message,
                email=lead_email,
                admin_email=admin_email,
            )


# Runs every day at 11:00 AM
@db_periodic_task(crontab(hour=11, minute=0))
def notify_funding_status() -> None:
    """Daily task to notify about funding status."""
    notify_funding_status_logic()


_template_charges_report = """
Dear {HoRSE},

Please find attached the charges report for the last month: {month}.

Best regards,
ProCAT
"""


def email_monthly_charges_report_logic(month: int, year: int, month_name: str) -> None:
    """Logic to email the HoRSE the charges report for the last month."""
    subject = f"Charges report for {month_name}"
    admin_email = get_admin_email()
    admin_name = get_admin_name()
    message = _template_charges_report.format(
        HoRSE=admin_name, month=month_name, year=year
    )
    csv_attachment = create_charges_report_for_attachment(month, year)

    email_attachment(
        subject,
        admin_email,
        message,
        f"charges_report_{month}-{year}.csv",
        csv_attachment,
        "text/csv",
    )


# Runs on the 10th day of every month at 10:00 AM
@db_periodic_task(crontab(day=10, hour=10))
def email_monthly_charges_report() -> None:
    """Email the HoRSE the charges report for the last month."""
    last_month_start, last_month_name, _, _ = get_current_and_last_month()
    email_monthly_charges_report_logic(
        last_month_start.month, last_month_start.year, last_month_name
    )


_template_budget_exceeded = """
Dear {lead},

The total charges for project {project_name} in the last month have exceeded
the budget.

Total charges: £{total_charges}
Budget: £{budget}

Please review the project budget and take necessary actions.

Best regards,
ProCAT
"""


def notify_monthly_charges_exceeding_budget_logic(
    date: datetime.datetime | None = None,
) -> None:
    """Logic to notify project lead and admin when total charges exceed budget.

    This function checks each project to see if the total charges from all of
    their funding sources for the last month exceed the budget. If they do,
    it sends an email notification to the project lead and admin.
    """
    if date is None:
        date = datetime.datetime.today()

    projects = get_projects_with_charges_exceeding_budget(date=date)

    for project, total_charges, total_budget in projects:
        lead = project.lead
        lead_name = lead.get_full_name() if lead else "Project Leader"
        lead_email = lead.email if lead else ""

        subject = f"[Monthly Charge Exceeding Budget] {project.name}"
        message = _template_budget_exceeded.format(
            lead=lead_name,
            project_name=project.name,
            total_charges=total_charges,
            budget=total_budget,
        )

        admin_email = get_admin_email()

        email_user_and_cc_admin(
            subject=subject,
            message=message,
            email=lead_email,
            admin_email=admin_email,
        )


# Runs every 7th day of the month at 9:30 AM
@db_periodic_task(crontab(day=7, hour=9, minute=30))
def notify_monthly_charges_exceeding_budget() -> None:
    """Monthly task to notify project leads and admin when budget exceeds."""
    notify_monthly_charges_exceeding_budget_logic()
