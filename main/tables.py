"""Tables needed by ProCAT."""

from decimal import Decimal
from typing import ClassVar

import django_tables2 as tables
from django.utils.safestring import mark_safe

from .models import Capacity, Funding, Project


class ProjectTable(tables.Table):
    """Table for Project listing."""

    name = tables.Column(linkify=("main:project_detail", {"pk": tables.A("pk")}))
    weeks_to_deadline = tables.Column(orderable=False)
    total_effort = tables.Column(orderable=False)
    days_left = tables.Column(orderable=False)

    class Meta:
        """Meta class for the table."""

        model = Project
        fields = (
            "name",
            "nature",
            "department",
            "status",
            "charging",
            "start_date",
            "end_date",
            "weeks_to_deadline",
            "total_effort",
            "days_left",
        )
        attrs: ClassVar[dict[str, str]] = {
            "class": "table table-striped table-hover table-responsive",
        }

    def render_weeks_to_deadline(self, value: tuple[int, float]) -> str:
        """Render the weeks_to_deadline with Bootstrap badge classes."""
        return self._style_fraction(value)

    def render_days_left(self, value: tuple[int, float]) -> str:
        """Render the days_left with Bootstrap badge classes."""
        return self._style_fraction(value)

    def _style_fraction(self, value: tuple[int, float]) -> str:
        """Render the fraction of days with Bootstrap badge classes.

        Args:
            value: The value to use to decide on the styling as a tuple. The first
            element is the absolute number, while the second is the fraction in %,
            actually used for styling.

        Return:
            Safe HTML string with the appropriate styling.
        """
        base_class = "badge text-white fs-5 opacity-75 px-3 py-2"
        num, frac = value

        if frac <= 10:
            return mark_safe(
                f'<span class="{base_class} bg-danger">{num} ({frac}%)</span>'
            )
        elif frac <= 30:
            return mark_safe(
                f'<span class="{base_class} bg-warning">{num} ({frac}%)</span>'
            )

        return mark_safe(
            f'<span class="{base_class} bg-success">{num} ({frac}%)</span>'
        )


class FundingTable(tables.Table):
    """Table for the Funding listing."""

    project = tables.Column(
        linkify=("main:project_detail", {"pk": tables.A("project.pk")})
    )
    project_code = tables.Column(
        linkify=("main:funding_detail", {"pk": tables.A("pk")}),
        order_by=("cost_centre", "activity"),
    )
    effort = tables.Column(orderable=False)
    effort_left = tables.Column(orderable=False)

    class Meta:
        """Meta class for the table."""

        model = Funding
        fields = (
            "project",
            "funding_body",
            "source",
            "project_code",
            "expiry_date",
            "budget",
            "effort",
            "effort_left",
        )
        attrs: ClassVar[dict[str, str]] = {
            "class": "table table-striped table-hover table-responsive",
        }


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

    def render_value(self, value: Decimal) -> str:
        """Render the value as a percentage."""
        return f"{value * 100:.0f}%"
