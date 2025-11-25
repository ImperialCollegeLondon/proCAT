"""Tables needed by ProCAT."""

from decimal import Decimal
from typing import ClassVar

import django_tables2 as tables
from django.db.models import QuerySet
from django.utils.safestring import mark_safe

from .models import Capacity, Funding, MonthlyCharge, Project
from .utils import format_currency, order_queryset_by_property


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
                "before any deductions are made."
            }
        },
    )

    days_left = tables.Column(
        verbose_name="Total days left",
        attrs={
            "th": {
                "title": "The total days remaining,\n"
                "after deducting all logged\n"
                "Clockify hours."
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

    def render_total_funding_left(self, value: Decimal) -> str:
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

    effort = tables.Column(
        attrs={
            "th": {
                "title": "The total effort in days available,\n"
                "before any deductions are made."
            }
        },
    )

    effort_left = tables.Column(
        attrs={
            "th": {
                "title": "The amount of days remaining,\n"
                "after deducting confirmed monthly\n"
                "charges."
            }
        },
    )

    funding_left = tables.Column(
        attrs={
            "th": {
                "title": "The amount of funding remaining,\n"
                "after deducting confirmed monthly\n"
                "charges."
            }
        },
    )

    def render_budget(self, value: Decimal) -> str:
        """Render the budget as a monetary value."""
        return format_currency(value)

    def order_effort(
        self, queryset: QuerySet[Funding], is_descending: bool
    ) -> tuple[QuerySet[Funding], bool]:
        """Order the effort column."""
        queryset = order_queryset_by_property(queryset, "effort", is_descending)
        return (queryset, True)

    def order_effort_left(
        self, queryset: QuerySet[Funding], is_descending: bool
    ) -> tuple[QuerySet[Funding], bool]:
        """Order the effort_left column."""
        queryset = order_queryset_by_property(queryset, "effort_left", is_descending)
        return (queryset, True)

    def render_funding_left(self, value: Decimal) -> str:
        """Render the funding left as a monetary value."""
        return format_currency(value)

    def order_funding_left(
        self, queryset: QuerySet[Funding], is_descending: bool
    ) -> tuple[QuerySet[Funding], bool]:
        """Order the funding_left column."""
        queryset = order_queryset_by_property(queryset, "funding_left", is_descending)
        return (queryset, True)

    class Meta:
        """Meta class for the table."""

        model = Funding
        fields = (
            "project_code",
            "project",
            "funding_body",
            "source",
            "expiry_date",
            "budget",
            "effort",
            "effort_left",
            "funding_left",
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


class MonthlyChargeTable(tables.Table):
    """Table for the Monthly Charge listing."""

    class Meta:
        """Meta class for the table."""

        model = MonthlyCharge
        fields = ("date", "amount", "status", "description")
        attrs: ClassVar[dict[str, str]] = {"class": "table table-striped"}
