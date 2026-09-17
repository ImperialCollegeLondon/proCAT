"""Tables needed by ProCAT."""

from typing import ClassVar

import django_tables2 as tables
from django.db.models import QuerySet

from .models import Capacity, Project
from .utils import format_currency, order_queryset_by_property, style_fraction_badge


class ProjectTable(tables.Table):
    """Table for Project listing."""

    name = tables.Column(
        linkify=("main:project_detail", {"pk": tables.A("pk")}),
        attrs={"th": {"style": "min-width: 150px;"}},
    )

    weeks_to_deadline = tables.Column(
        attrs={
            "th": {"title": "The number of weeks left until the\nproject deadline."}
        },
    )

    total_effort = tables.Column(
        attrs={
            "th": {
                "title": "The total effort in days available,\n"
                "including all funding sources,\n"
                "before any deductions are made.\n"
                "For projects in Maintenance, this\n"
                "accounts only for that phase.\n"
                "For projects in Active status with\n"
                "phases defined, this accounts only\n"
                "for the non-maintenance phases.\n"
            }
        },
    )

    days_left = tables.Column(
        verbose_name="Total days left",
        attrs={
            "th": {
                "title": "The total days remaining,\n"
                "after deducting all logged hours.\n"
                "For projects in Maintenance, this \n"
                "accunts for the time logged and the\n"
                "time that has passed in the phase, pro-rata.\n"
            }
        },
    )

    total_funding_left = tables.Column(
        attrs={
            "th": {
                "title": "The total funding remaining,\n"
                "including all funding sources,\n"
                "after deducting confirmed charges."
            }
        },
    )

    def order_weeks_to_deadline(
        self, queryset: QuerySet[Project], is_descending: bool
    ) -> tuple[QuerySet[Project], bool]:
        """Order the weeks to deadline column."""
        queryset = order_queryset_by_property(
            queryset, "weeks_to_deadline", is_descending
        )
        return (queryset, True)

    def order_total_effort(
        self, queryset: QuerySet[Project], is_descending: bool
    ) -> tuple[QuerySet[Project], bool]:
        """Order the total effort column."""
        queryset = order_queryset_by_property(queryset, "total_effort", is_descending)
        return (queryset, True)

    def order_days_left(
        self, queryset: QuerySet[Project], is_descending: bool
    ) -> tuple[QuerySet[Project], bool]:
        """Order the days left column."""
        queryset = order_queryset_by_property(queryset, "days_left", is_descending)
        return (queryset, True)

    def render_total_funding_left(self, value: float) -> str:
        """Render the total funding left as a monetary value."""
        return format_currency(value)

    def order_total_funding_left(
        self, queryset: QuerySet[Project], is_descending: bool
    ) -> tuple[QuerySet[Project], bool]:
        """Order the total funding left column."""
        queryset = order_queryset_by_property(
            queryset, "total_funding_left", is_descending
        )
        return (queryset, True)

    class Meta:
        """Meta class for the table."""

        model = Project
        fields = (
            "name",
            "nature",
            "department",
            "charging",
            "start_date",
            "end_date",
            "weeks_to_deadline",
            "total_effort",
            "days_left",
            "total_funding_left",
        )
        attrs: ClassVar[dict[str, str]] = {
            "class": "table table-striped table-hover table-responsive",
        }

    def render_weeks_to_deadline(self, value: tuple[int, float]) -> str:
        """Render the weeks_to_deadline with Bootstrap badge classes."""
        return style_fraction_badge(value)

    def render_days_left(self, value: tuple[int, float]) -> str:
        """Render the days_left with Bootstrap badge classes."""
        return style_fraction_badge(value)

    def render_total_effort(self, value: float) -> str:
        """Render the total effort left with just two decimals."""
        return str(round(value, 2))


class CapacityTable(tables.Table):
    """Table for Capacity listing."""

    class Meta:
        """Meta class for the table."""

        model = Capacity
        fields = (
            "user",
            "value",
            "start_date",
        )
        attrs: ClassVar[dict[str, str]] = {
            "class": "table table-striped table-hover table-responsive",
        }

    def render_value(self, value: float) -> str:
        """Render the value as a percentage."""
        return f"{value * 100:.0f}%"
