"""General utilities for ProCAT."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from . import models
from .models import Funding, Project, TimeEntry

ANALYSIS_CODES = (
    {
        "code": 182130,
        "description": "FEC Directly Allocated EQP&FACILITIES",
        "notes": "FEC-like projects (typically UKRI, but could be others) at the "
        "pre-award stage (DA) - P accounts only",
    },
    {
        "code": 165133,
        "description": "FACILITIES USAGE (DI FEC PROJECTS)",
        "notes": "FEC-like projects (typically UKRI, but could be others) when costs"
        " were not budgeted (DI) - P accounts only",
    },
    {
        "code": 165134,
        "description": "CHG OUT FACILITY/NON-FEC",
        "notes": "Non-FEC projects (typically charities) in all cases (DI) - P accounts"
        " only",
    },
    {
        "code": 165138,
        "description": "FACILITIES USAGE (Internal funds)",
        "notes": "Used if charged to non-research accounts - NOT P accounts",
    },
)


def create_analysis(*args: Any) -> None:  # type: ignore [explicit-any]
    """Create default analysis codes."""
    models.AnalysisCode.objects.bulk_create(
        [models.AnalysisCode(**ac) for ac in ANALYSIS_CODES]
    )


def destroy_analysis(*args: Any) -> None:  # type: ignore [explicit-any]
    """Delete default analysis codes."""
    codes = [ac["code"] for ac in ANALYSIS_CODES]
    models.AnalysisCode.objects.filter(code__in=codes).delete()


def get_logged_hours(
    entries: Iterable["TimeEntry"],
) -> tuple[float, str]:
    """Calculate total logged hours from time entries."""
    project_hours: defaultdict[str, float] = defaultdict(
        float
    )  # <- This defaults to 0.0
    total_hours = 0.0

    for entry in entries:
        project_name = entry.project.name
        hours = (entry.end_time - entry.start_time).total_seconds() / 3600
        total_hours += hours
        project_hours[project_name] += hours

    project_work_summary = "\n".join(
        [
            f"{project}: {round(hours / 7, 1)} days"
            # Assuming 7 hours/workday
            for project, hours in project_hours.items()
        ]
    )

    return total_hours, project_work_summary


def get_current_and_last_month(
    date: datetime | None = None,
) -> tuple[datetime, str, datetime, str]:
    """Get the start of the last month and current month, and their names."""
    if date is None:
        date = datetime.today()

    current_month_start = datetime(year=date.year, month=date.month, day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    last_month_name = last_month_start.strftime("%B")
    current_month_name = current_month_start.strftime("%B")

    return (
        last_month_start,
        last_month_name,
        current_month_start,
        current_month_name,
    )


def get_admin_email() -> list[str]:
    """Get the email of the first superuser."""
    User = get_user_model()
    admin_email = (
        User.objects.filter(is_superuser=True).values_list("email", flat=True).first()
    )
    return [admin_email] if admin_email else []


def get_admin_name() -> str | None:
    """Get the name of the first superuser."""
    User = get_user_model()
    admin_name = User.objects.filter(is_superuser=True).first()
    return admin_name.get_full_name() if admin_name else None


def get_budget_status(
    date: date | None = None,
) -> tuple[QuerySet[Funding], QuerySet[Funding]]:
    """Get the budget status of a funding."""
    if date is None:
        date = datetime.today().date()

    funds_ran_out_not_expired = Funding.objects.filter(
        expiry_date__gt=date, budget__lt=0
    )
    funding_expired_budget_left = Funding.objects.filter(
        expiry_date__lt=date, budget__gt=0
    )
    return funds_ran_out_not_expired, funding_expired_budget_left


def get_month_dates_for_previous_year() -> list[tuple[date, date]]:
    """Get the start and end date of each month for the previous year."""
    dates = []
    today = datetime.today().date()

    start_current_month = today.replace(day=1)
    for _ in range(12):
        end_prev_month = start_current_month - timedelta(days=1)
        start_prev_month = end_prev_month.replace(day=1)
        dates.append((start_prev_month, end_prev_month))
        start_current_month = start_prev_month

    dates.reverse()
    return dates



def get_projects_with_charges_exceeding_budget(
    date: datetime | None = None,
) -> list[tuple[Project, Decimal, Decimal]]:
    """Get projects whose monthly charges (for the last month) exceed their budget.

    This function returns projects whose total charges
    in the last month exceed the total budget available from all active
    funding sources.
    """
    if date is None:
        date = datetime.today()

    projects_with_charges_exceeding_budget = []

    last_month_start, _, current_month_start, _ = get_current_and_last_month(date)

    projects = Project.objects.filter(status="Active")

    for project in projects:
        funding_sources = Funding.objects.filter(project=project)
        if not funding_sources.exists():
            continue  # No funding sources for this project
        total_hours = Decimal("0.0")

        time_entries = TimeEntry.objects.filter(
            project=project,
            start_time__gte=last_month_start,
            end_time__lt=current_month_start,
        )

        if not time_entries.exists():
            continue

        for entry in time_entries:
            duration = (entry.end_time - entry.start_time).total_seconds()
            total_hours += Decimal(str(duration / 3600))

        active_funding = Funding.objects.filter(
            project=project,
            expiry_date__gte=current_month_start,
            budget__gt=0,
        )

        total_active_budget = sum(
            (fund.funding_left for fund in active_funding), Decimal("0.0")
        )

        rates = list(active_funding.values_list("daily_rate", flat=True))
        if not rates:
            continue

        avg_daily_rate = sum(rates) / len(rates)

        total_charges = (total_hours / Decimal("7")) * Decimal(
            str(avg_daily_rate)
        )  # Assuming 7 hours per workday

        if total_charges > total_active_budget:
            projects_with_charges_exceeding_budget.append(
                (project, total_charges, total_active_budget)
            )

    return projects_with_charges_exceeding_budget