"""Tables needed by ProCAT."""

import django_tables2 as tables

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
        )
