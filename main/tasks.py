"""Task definitions for project notifications using Huey."""

import datetime

from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from .models import Project
from .notify import notify_lead


# Runs every monday at 10:00 AM
@db_periodic_task(crontab(hour=10, minute=0, day_of_week=1))
def notify_project_due_completion_soon() -> None:
    """Notify about project(s) due for completion soon."""
    projects = Project.objects.filter(
        status="Active",
        end_date__lte=datetime.datetime.now() + datetime.timedelta(days=7),
    )

    for project in projects:
        notify_lead(project)
