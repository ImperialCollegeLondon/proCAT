"""Functions for calculating team activity stats."""

from collections import Counter, defaultdict
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


def get_funding_per_department(projects: list[models.Project]) -> dict[str, float]:
    """Determine the total project funding per department.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with department names and the project funding per department.
    """
    funding_per_department: dict[str, float] = defaultdict(float)
    for project in projects:
        funding_per_department[project.department.name] += float(
            sum([funding.budget for funding in project.funding_source.all()])
        )
    return funding_per_department


def get_funding_per_faculty(projects: list[models.Project]) -> dict[str, float]:
    """Determine the total project funding per faculty.

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with faculty names and the project funding per faculty.
    """
    funding_per_faculty: dict[str, float] = defaultdict(float)
    for project in projects:
        funding_per_faculty[project.department.faculty] += float(
            sum([funding.budget for funding in project.funding_source.all()])
        )
    return funding_per_faculty

def get_project_count_per_budget_type(projects: list[models.Project]) -> dict[str, int]:
    """Determine the number of projects per type of budget.

    Budget types are:
    1. Internal (internal projects)
    2. External FEC DI (directly incurred)
    3. External FEC DA (directly allocated)
    4. External Non-FEC
    5. Other (internal funds for external projects)

    Args:
        projects: The list of projects.

    Returns:
        A dictionary with budget types and the number of projects per type.
    """
    # Select only funding instances that fund one of the input queried projects
    project_fundings = models.Funding.objects.filter(project__in=projects)

    # Categorise according to funding source
    budget_types = ["Internal" for _ in project_fundings.filter(source="Internal")]
    budget_types += [
        "Other" for _ in project_fundings.filter(analysis_code__code=165138)
    ]
    budget_types += [
        "FEC DI" for _ in project_fundings.filter(analysis_code__code=165133)
    ]
    budget_types += [
        "FEC DA" for _ in project_fundings.filter(analysis_code__code=182130)
    ]
    budget_types += [
        "Non-FEC" for _ in project_fundings.filter(analysis_code__code=165134)
    ]

    return Counter(budget_types)

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
