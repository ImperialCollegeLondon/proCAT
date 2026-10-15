"""Functions for calculating team activity stats."""

from datetime import date

from django.db.models import QuerySet

from .models import Project


def _get_num_projects_per_division(divs: list[str]) -> dict[str, int]:
    """Determine the number of projects per division.

    A "division" could be a department or faculty, for example.

    Args:
        divs: The list of names of divisions.

    Returns:
        A dictionary with division names and the number of projects per division.
    """
    return {div: divs.count(div) for div in divs}


def get_num_projects_per_department(projects: list[Project]) -> dict[str, int]:
    """Determine the number of projects per department.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with department names and the number of projects per department.
    """
    departments = [project.department.name for project in projects]
    return _get_num_projects_per_division(departments)


def get_num_projects_per_faculty(projects: list[Project]) -> dict[str, int]:
    """Determine the number of projects per faculty.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with faculty names and the number of projects per faculty.
    """
    faculties = [project.department.faculty for project in projects]
    return _get_num_projects_per_division(faculties)


def get_projects_active_in_past_year(projects: QuerySet[Project]) -> list[Project]:
    """Get the projects in the past year.

    Here we are concerned with projects that were active in the past 12 months. This
    includes projects that began within the last 12 months, and projects that finished
    within the last 12 months.

    Exclude "Not done", which is projects whose start date has passed, but are not yet
    under development.

    Args:
        projects: The set of projects.

    Returns:
        The list of projects under active development within the past year.
    """
    today = date.today()
    one_year_ago = date(today.year - 1, today.month, today.day)

    return list(
        projects.exclude(status="Not done").filter(
            start_date__lt=today, end_date__gte=one_year_ago
        )
    )
