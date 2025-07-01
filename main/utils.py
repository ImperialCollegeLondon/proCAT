"""General utilities for ProCAT."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model

from . import models
from .models import TimeEntry

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
