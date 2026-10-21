"""Functions for calculating team activity stats."""

from datetime import date

from django.http import HttpRequest
from ninja import NinjaAPI

from . import models

api = NinjaAPI()


def _str_to_date(date_str: str) -> date:
    """Convert a DD/MM/YYYY string to a datetime.date.

    Args:
        date_str: A date in the format DD/MM/YYYY.

    Returns:
        The provided date, as a datetime.date.
    """
    date_str_split = date_str.split("/")
    date_str_split.reverse()
    date_int_split = [int(s) for s in date_str_split]
    return date(*date_int_split)


def _get_num_projects_per_division(divs: list[str]) -> dict[str, int]:
    """Determine the number of projects per division.

    A "division" could be a department or faculty, for example.

    Args:
        divs: The list of names of divisions.

    Returns:
        A dictionary with division names and the number of projects per division.
    """
    return {div: divs.count(div) for div in divs}


def get_num_projects_per_department(projects: list[models.Project]) -> dict[str, int]:
    """Determine the number of projects per department.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with department names and the number of projects per department.
    """
    departments = [project.department.name for project in projects]
    return _get_num_projects_per_division(departments)


def get_num_projects_per_faculty(projects: list[models.Project]) -> dict[str, int]:
    """Determine the number of projects per faculty.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with faculty names and the number of projects per faculty.
    """
    faculties = [project.department.faculty for project in projects]
    return _get_num_projects_per_division(faculties)


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


@api.get("/data/projects_by_department")
def get_projects_by_department(
    request: HttpRequest, from_date: str, to_date: str
) -> dict[str, int]:
    """Determine the number of projects per department.

    Args:
        request: The HTTP request.
        from_date: A date in the format DD/MM/YYYY.
        to_date: A date in the format DD/MM/YYYY.

    Returns:
        A dictionary of projects active in the requested interval, separated by
        department.
    """
    projects = get_projects_active_between(
        _str_to_date(from_date), _str_to_date(to_date)
    )
    return get_num_projects_per_department(projects)


@api.get("/data/projects_by_faculty")
def get_projects_by_faculty(
    request: HttpRequest, from_date: str, to_date: str
) -> dict[str, int]:
    """Determine the number of projects per faculty.

    Args:
        request: The HTTP request.
        from_date: A date in the format DD/MM/YYYY.
        to_date: A date in the format DD/MM/YYYY.

    Returns:
        A dictionary of projects active in the requested interval, separated by faculty.
    """
    projects = get_projects_active_between(
        _str_to_date(from_date), _str_to_date(to_date)
    )
    return get_num_projects_per_faculty(projects)
