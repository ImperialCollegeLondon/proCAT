"""Tables needed by ProCAT."""

from typing import ClassVar

import django_tables2 as tables
from django.utils.safestring import mark_safe

from .models import Project


class ProjectTable(tables.Table):
    """Table for Project listing."""

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
            "fraction_days_left",
            "fraction_effort_left",
        )
        attrs: ClassVar[dict[str, str]] = {
            "class": "table table-striped table-hover table-responsive",
        }

    def render_fraction_days_left(self, value: float) -> str:
        """Render the fraction_days_left with Bootstrap badge classes."""
        return self._style_fraction(value)

    def render_fraction_effort_left(self, value: float) -> str:
        """Render the fraction_effort_left with Bootstrap badge classes."""
        return self._style_fraction(value)

    def _style_fraction(self, value: float) -> str:
        """Render the fraction of days with Bootstrap badge classes.

        Args:
            value: The value to use to decide on the styling.

        Return:
            Safe HTML string with the appropriate styling.
        """
        base_class = "badge text-white fs-5 opacity-75 px-3 py-2"

        if value <= 10:
            return mark_safe(f'<span class="{base_class} bg-danger">{value}%</span>')
        elif value <= 30:
            return mark_safe(f'<span class="{base_class} bg-warning">{value}%</span>')

        return mark_safe(f'<span class="{base_class} bg-success">{value}%</span>')
