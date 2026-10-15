"""Unit tests for the analytics module."""

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from main.analytics import (
    _get_num_projects_per_division,
    get_num_projects_per_department,
    get_num_projects_per_faculty,
    get_projects_active_in_past_year,
)
from main.models import Department, Project


@pytest.fixture
def projects_list(db):
    """A list of projects to cover a broad range of attributes.

    Aim to cover a range of departments, faculties, start and end dates and statuses.
    """
    department_list = [
        Department(name="Mathematics", faculty="Faculty of Natural Sciences"),
        Department(name="Computing", faculty="Faculty of Engineering"),
        Department(name="Materials", faculty="Faculty of Engineering"),
        Department(name="Physics", faculty="Faculty of Natural Sciences"),
        Department(name="Immunology and Inflammation", faculty="Faculty of Medicine"),
        Department(name="ICT", faculty="Other"),
    ]
    Department.objects.bulk_create(department_list)

    projects_list = [
        Project(
            name="Calcul8",
            department=Department.objects.get(name="Mathematics"),
            start_date="2023-02-01",
            end_date="2026-05-04",
            status="Finished",
        ),
        Project(
            name="ProjectX",
            department=Department.objects.get(name="Computing"),
            start_date="2026-05-04",
            end_date="2029-08-07",
            status="Not done",
        ),
        Project(
            name="Picobots",
            department=Department.objects.get(name="Materials"),
            start_date="2023-02-01",
            end_date="2027-01-01",
            status="Active",
        ),
        Project(
            name="Astro0",
            department=Department.objects.get(name="Physics"),
            start_date="2028-07-06",
            end_date="2039-12-31",
            status="Tentative",
        ),
        Project(
            name="Rust++",
            department=Department.objects.get(name="Computing"),
            start_date="2027-01-10",
            end_date="2028-01-09",
            status="Confirmed",
        ),
        Project(
            name="Vaxin7",
            department=Department.objects.get(name="Immunology and Inflammation"),
            start_date="2024-04-04",
            end_date="2025-05-05",
            status="Finished",
        ),
        Project(
            name="Vaxin8",
            department=Department.objects.get(name="Immunology and Inflammation"),
            start_date="2025-05-05",
            end_date="2028-08-08",
            status="Maintenance",
        ),
        Project(
            name="Great Project",
            department=Department.objects.get(name="ICT"),
            start_date="2023-02-01",
            end_date="2029-08-07",
            status="Active",
        ),
    ]

    Project.objects.bulk_create(projects_list)

    return projects_list


def test_get_num_projects_per_division():
    """Test the _get_num_projects_per_division function."""
    divs = ["a"] * 8 + ["b"] * 5 + ["c"] * 21
    assert _get_num_projects_per_division(divs) == {"a": 8, "b": 5, "c": 21}


def test_get_num_projects_per_department(projects_list: list[Project]):
    """Test the get_num_projects_per_department function.

    projects_list fixture contains:
    - 1 Mathematics
    - 2 Computing
    - 1 Materials
    - 1 Physics
    - 2 Immunology and Inflammation
    - 1 ICT
    """
    proj_per_dept = get_num_projects_per_department(projects_list)

    assert proj_per_dept["Mathematics"] == 1
    assert proj_per_dept["Computing"] == 2
    assert proj_per_dept["Materials"] == 1
    assert proj_per_dept["Physics"] == 1
    assert proj_per_dept["Immunology and Inflammation"] == 2
    assert proj_per_dept["ICT"] == 1


def test_get_num_projects_per_faculty(projects_list: list[Project]):
    """Test the get_num_projects_per_faculty function.

    projects_list fixture contains:
    - 2 FoNS,
    - 3 FoE,
    - 2 FoM,  codespell:ignore
    - 0 IBS,
    - 1 Other
    """
    proj_per_faculty = get_num_projects_per_faculty(projects_list)

    assert proj_per_faculty["Faculty of Natural Sciences"] == 2
    assert proj_per_faculty["Faculty of Engineering"] == 3
    assert proj_per_faculty["Faculty of Medicine"] == 2
    assert proj_per_faculty.get("Imperial Business School") is None
    assert proj_per_faculty["Other"] == 1


@patch("main.analytics.date")
def test_get_projects_active_in_past_year(
    date_mock: MagicMock, projects_list: list[Project]
):
    """Test the get_num_projects_per_department function."""
    date_mock.today.return_value = dt.date(2026, 10, 14)
    date_mock.side_effect = lambda *args, **kw: dt.date(*args, **kw)

    projects = get_projects_active_in_past_year(Project.objects.all())

    # Finished in past 12 months
    assert Project.objects.get(name="Calcul8") in projects

    # Project initiated, but work not started
    assert Project.objects.get(name="ProjectX") not in projects

    # Started, not finished
    assert Project.objects.get(name="Picobots") in projects

    # Future start date (tentative)
    assert Project.objects.get(name="Astro0") not in projects

    # Future start date (confirmed)
    assert Project.objects.get(name="Rust++") not in projects

    # Finished more than 12 months ago
    assert Project.objects.get(name="Vaxin7") not in projects

    # Currently in maintenance period
    assert Project.objects.get(name="Vaxin8") in projects

    # Started, not finished
    assert Project.objects.get(name="Great Project") in projects
