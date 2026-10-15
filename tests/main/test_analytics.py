"""Unit tests for the analytics module."""

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from main.analytics import (
    _get_num_projects_per_division,
    _str_to_date,
    get_num_projects_per_department,
    get_num_projects_per_faculty,
    get_projects_active_in_past_year,
)
from main.models import Department, Project


@pytest.fixture
def projects_list():
    """A list of projects to cover a broad range of attributes.

    Aim to cover a range of departments, faculties, start and end dates and statuses.
    """
    return [
        Project(
            name="Calcul8",
            department=Department(
                name="Mathematics", faculty="Faculty of Natural Sciences"
            ),
            start_date="01/02/2023",
            end_date="04/05/2026",
            status="Finished",
        ),
        Project(
            name="ProjectX",
            department=Department(name="Computing", faculty="Faculty of Engineering"),
            start_date="04/05/2026",
            end_date="07/08/2029",
            status="Not done",
        ),
        Project(
            name="Picobots",
            department=Department(name="Materials", faculty="Faculty of Engineering"),
            start_date="01/02/2023",
            end_date="01/01/2027",
            status="Active",
        ),
        Project(
            name="Astro0",
            department=Department(
                name="Physics", faculty="Faculty of Natural Sciences"
            ),
            start_date="06/07/2028",
            end_date="31/12/2039",
            status="Tentative",
        ),
        Project(
            name="Rust++",
            department=Department(name="Computing", faculty="Faculty of Engineering"),
            start_date="10/01/2027",
            end_date="09/01/2028",
            status="Confirmed",
        ),
        Project(
            name="Vaxin7",
            department=Department(
                name="Immunology and Inflammation",
                faculty="Faculty of Medicine",
            ),
            start_date="04/04/2024",
            end_date="05/05/2025",
            status="Finished",
        ),
        Project(
            name="Vaxin8",
            department=Department(
                name="Immunology and Inflammation",
                faculty="Faculty of Medicine",
            ),
            start_date="05/05/2025",
            end_date="08/08/2028",
            status="Maintenance",
        ),
        Project(
            name="Great Project",
            department=Department(name="ICT", faculty="Other"),
            start_date="01/02/2023",
            end_date="07/08/2029",
            status="Active",
        ),
    ]


def test_str_to_date():
    """Test the _str_to_date function."""
    assert _str_to_date("01/02/2023") == dt.date(2023, 2, 1)
    assert _str_to_date("04/5/2026") == dt.date(2026, 5, 4)
    assert _str_to_date("7/08/2029") == dt.date(2029, 8, 7)


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

    projects = get_projects_active_in_past_year(projects_list)

    calcul8 = next(project for project in projects_list if project.name == "Calcul8")
    assert calcul8 in projects  # Finished in past 12 months

    projectx = next(project for project in projects_list if project.name == "ProjectX")
    assert projectx not in projects  # Project initiated, but work not started

    picobots = next(project for project in projects_list if project.name == "Picobots")
    assert picobots in projects  # Started, not finished

    astro0 = next(project for project in projects_list if project.name == "Astro0")
    assert astro0 not in projects  # Future start date (tentative)

    rustpp = next(project for project in projects_list if project.name == "Rust++")
    assert rustpp not in projects  # Future start date (confirmed)

    vaxin7 = next(project for project in projects_list if project.name == "Vaxin7")
    assert vaxin7 not in projects  # Finished more than 12 months ago

    vaxin8 = next(project for project in projects_list if project.name == "Vaxin8")
    assert vaxin8 in projects  # Currently in maintenance period

    great_project = next(
        project for project in projects_list if project.name == "Great Project"
    )
    assert great_project in projects  # Started, not finished
