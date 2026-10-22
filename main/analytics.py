"""Functions for calculating team activity stats."""

from collections import Counter
from datetime import date

from . import models


def get_project_count_per_department(projects: list[models.Project]) -> dict[str, int]:
    """Determine the number of projects per department.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with department names and the number of projects per department.
    """
    return Counter([project.department.name for project in projects])


def get_project_count_per_faculty(projects: list[models.Project]) -> dict[str, int]:
    """Determine the number of projects per faculty.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with faculty names and the number of projects per faculty.
    """
    return Counter([project.department.faculty for project in projects])


def get_projects_active_between(from_date: date, to_date: date) -> list[models.Project]:
    """Get the projects under active development within a time frame.

    Exclude "Not done", which is projects whose start date has passed, but are not under
    development.

    Args:
        from_date: A datetime.date marking the start of the search interval.
        to_date: A datetime.date marking the end of the search interval.

    Returns:
        The list of projects under active development within the time interval.
    """
    return list(
        models.Project.objects.exclude(status="Not done").filter(
            start_date__lt=to_date, end_date__gte=from_date
        )
    )
