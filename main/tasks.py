"""Task definitions for project notifications using Huey."""

import datetime
import logging

from django.conf import settings
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

from .Clockify.api_interface import ClockifyAPI
from .models import Project, TimeEntry, User
from .notify import email_attachment, email_user, email_user_and_cc_head
from .report import create_charges_report_for_attachment
from .utils import (
    get_budget_status,
    get_current_and_last_month,
    get_head_email,
    get_logged_hours,
    get_projects_with_days_used_exceeding_days_left,
)

logger = logging.getLogger(__name__)

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
            head_email = get_head_email()
            lead = funding.project.lead
            lead_name = lead.get_full_name() if lead is not None else "Project Leader"
            lead_email = lead.email if lead is not None else ""
            activity = funding.activity if funding.activity else "Funding Activity"
            message = _template_funds_ran_out_but_not_expired.format(
                lead=lead_name,
                project_name=funding.project.name,
                activity=activity,
            )
            email_user_and_cc_head(
                subject=subject,
                message=message,
                email=lead_email,
                head_email=head_email,
            )

    if funding_expired_budget_left.exists():
        for funding in funding_expired_budget_left:
            subject = f"[Funding Expired] {funding.project.name}"
            head_email = get_head_email()
            lead = funding.project.lead
            lead_name = lead.get_full_name() if lead is not None else "Project Leader"
            lead_email = lead.email if lead is not None else ""
            message = _template_funding_expired_but_has_budget.format(
                lead=lead_name,
                project_name=funding.project.name,
                budget=funding.budget,
            )
            email_user_and_cc_head(
                subject=subject,
                message=message,
                email=lead_email,
                head_email=head_email,
            )


# Runs every day at 11:00 AM
@db_periodic_task(crontab(hour=11, minute=0))
def notify_funding_status() -> None:
    """Daily task to notify about funding status."""
    notify_funding_status_logic()


_template_charges_report = """
Dear Head of the RSE team,

Please find attached the charges report for the last month: {month}/{year}.

Best regards,
ProCAT
"""


def email_monthly_charges_report_logic(month: int, year: int, month_name: str) -> None:
    """Logic to email the HoRSE the charges report for the last month."""
    subject = f"Charges report for {month_name}/{year}"
    head_email = get_head_email()
    message = _template_charges_report.format(month=month_name, year=year)
    csv_attachment = create_charges_report_for_attachment(month, year)

    email_attachment(
        subject,
        head_email,
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


def sync_clockify_time_entries(
    days_back: int = 30,
    end_date: datetime.datetime = timezone.now(),
    pageSize: int = 200,
) -> None:
    """Task to sync time entries from Clockify API to TimeEntry model."""
    if not settings.CLOCKIFY_API_KEY or not settings.CLOCKIFY_WORKSPACE_ID:
        logger.warning("Clockify API key not found in environment variables")
        return
    api = ClockifyAPI(settings.CLOCKIFY_API_KEY, settings.CLOCKIFY_WORKSPACE_ID)
    start_date = end_date - datetime.timedelta(days=days_back)

    projects = Project.objects.filter(status="Active").exclude(clockify_id="")
    for project in projects:
        logger.info(f"Processing project ID: {project.clockify_id}")
        payload = {
            "dateRangeStart": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
            "dateRangeEnd": end_date.strftime("%Y-%m-%dT23:59:59.000Z"),
            "detailedFilter": {"page": 1, "pageSize": pageSize},
            "projects": {"contains": "CONTAINS", "ids": [project.clockify_id]},
        }

        try:
            response = api.get_time_entries(payload)
        except Exception as e:
            logger.error(
                f"Error fetching time entries for project {project.clockify_id}: {e}"
            )
            continue

        entries = response.get("timeentries", [])
        if not isinstance(entries, list):
            entries = []

        for entry in entries:
            entry_id = entry.get("id") or entry.get("_id")
            project_id = entry.get("projectId")
            user_email = entry.get("userEmail")
            time_interval = entry.get("timeInterval", {})
            start = time_interval.get("start")
            end = time_interval.get("end")

            if not (project_id and user_email and start and end):
                logger.warning(f"Skipping incomplete entry: {entry_id}")
                continue

            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                logger.warning(
                    f"User {user_email} not found. Skipping entry {entry_id}."
                )
                continue

            start_time = datetime.datetime.fromisoformat(start)
            end_time = datetime.datetime.fromisoformat(end)

            TimeEntry.objects.get_or_create(
                clockify_id=entry_id,
                defaults={
                    "user": user,
                    "project": project,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )


@db_periodic_task(crontab(day_of_week="mon", hour=2, minute=0))
def sync_clockify_time_entries_task() -> None:
    """Scheduled task to sync time entries from Clockify API."""
    sync_clockify_time_entries()
    logger.info("Clockify time entries sync completed.")


_template_days_used_exceeded_days_left = """
Dear {lead},

The total days used for project {project_name} has exceeded the days left
for the project.

Days used: {days_used}
Days left: {days_left}

Please review the project budget and take necessary actions.

Best regards,
ProCAT
"""


def notify_monthly_days_used_exceeding_days_left_logic(
    date: datetime.datetime | None = None,
) -> None:
    """Logic to notify project lead and HoRSE if total days used exceed days left.

    This function checks each project to see if the days used for the
    project exceed the days left. If they do,
    it sends an email notification to the project lead and HoRSE.
    """
    if date is None:
        date = datetime.datetime.today()

    projects = get_projects_with_days_used_exceeding_days_left(date=date)

    for project, days_used, days_left in projects:
        lead = project.lead
        lead_name = lead.get_full_name() if lead else "Project Leader"
        lead_email = lead.email if lead else ""

        subject = f"[Monthly Days Used Exceed Days Left] {project.name}"
        message = _template_days_used_exceeded_days_left.format(
            lead=lead_name,
            project_name=project.name,
            days_used=days_used,
            days_left=days_left,
        )

        head_email = get_head_email()

        email_user_and_cc_head(
            subject=subject,
            message=message,
            email=lead_email,
            head_email=head_email,
        )


# Runs every 7th day of the month at 9:30 AM
@db_periodic_task(crontab(day=7, hour=9, minute=30))
def notify_monthly_days_used_exceeding_days_left() -> None:
    """Monthly task to notify project leads and HoRSE if days used exceed days left."""
    notify_monthly_days_used_exceeding_days_left_logic()
