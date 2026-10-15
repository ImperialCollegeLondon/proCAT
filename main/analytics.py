"""Functions for calculating team activity stats."""

from datetime import date

from .models import Project


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


def get_projects_active_in_past_year(projects: list[Project]) -> list[Project]:
    """Get the projects in the past year.

    Here we are concerned with projects that were active in the past 12 months. This
    includes projects that began within the last 12 months, and projects that finished

    Args:
        projects: The list of projects.

    Returns:
        The list of projects started within the past year.
    """
    today = date.today()
    one_year_ago = date(today.year - 1, today.month, today.day)

    return [
        project
        for project in projects
        if _str_to_date(project.start_date) < today
        and _str_to_date(project.end_date) > one_year_ago
        and project.status != "Not done"  # "Not done" implies work not yet started
    ]
