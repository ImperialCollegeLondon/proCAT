"""General utilities for ProCAT."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Case, When
from django.db.models.query import QuerySet

from . import models
from .models import Funding, TimeEntry

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


def order_queryset_by_property(  # type: ignore[explicit-any]
    queryset: QuerySet[Any], property: str, is_descending: bool
) -> QuerySet[Any]:
    """Orders a queryset according to a specified Model property.

    Creates a Django conditional expression to assign the position
    of the model in a queryset according to its model ID (using a
    custom ordering). The conditional expression is then provided to
    the QuerySet.order_by() function. This can be used to update the
    ordering of a queryset column in a Table.

    Args:
        queryset: a model queryset for ordering
        property: the name of the model property with which to order
            the queryset
        is_descending: bool to indicate whether the property should
            be sorted by descending (or ascending) order

    Returns:
        The queryset ordered according to the property.
    """
    model_ids = list(queryset.values_list("id", flat=True))
    values = [getattr(obj, property) for obj in queryset]
    sorted_indexes = sorted(
        range(len(values)), key=lambda i: values[i], reverse=is_descending
    )
    # Create conditional expression using custom ordering
    preserved_ordering = Case(
        *[
            When(id=model_ids[id], then=position)
            for position, id in enumerate(sorted_indexes)
        ]
    )
    queryset = queryset.order_by(preserved_ordering)
    return queryset
