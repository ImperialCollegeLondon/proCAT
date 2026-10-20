"""Functions for calculating team activity stats."""

from datetime import date

import pandas as pd
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
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

    Exclude "Not done", which is projects whose start date has passed, but are not yet
    under development.

    Args:
        from_date: A datetime.date marking the start of the search interval.
        to_date:  A datetime.date marking the end of the search interval.

    Returns:
        The list of projects under active development within the time interval.
    """
    projects = models.Project.objects.all()
    return list(
        projects.exclude(status="Not done").filter(
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


def _assemble_projects_summary() -> pd.DataFrame:
    """Summarise project data in a dataframe.

    Returns:
        DataFrame with columns:
            month: "YYYY-MM".
            faculty: faculty the department belongs to.
            department: department name.
            n_projects_active: projects running that month.
            budget_active: total budget of active projects.
            n_projects_started: projects that started that month.
            n_projects_finished: projects that finished that month (i.e. no
                longer active, the month after their end_date).
    """
    today = timezone.now().date()
    data_query = (
        models.Project.objects.exclude(status="Not done")
        .filter(start_date__lte=today)
        .values(
            "pk", "start_date", "end_date", "department__name", "department__faculty"
        )
    )
    data = pd.DataFrame.from_records(data_query).rename(
        columns={"department__name": "department", "department__faculty": "faculty"}
    )

    def _budget(x):
        b = models.Funding.objects.filter(project=x["pk"]).values_list(
            "budget", flat=True
        )
        return sum(b) if b else 0.0

    data["budget"] = data.apply(_budget, axis=1)
    aggregated = _aggregate_projects_by_month_department(data)
    return aggregated


def _aggregate_projects_by_month_department(df: pd.DataFrame) -> pd.DataFrame:
    """Build a month x department summary of project activity.

    Args:
        df: Must contain columns "pk", "budget", "start_date", "end_date",
            "department", "faculty".

    Returns:
        DataFrame with columns:
            month: "YYYY-MM".
            faculty: faculty the department belongs to.
            department: department name.
            n_projects_active: projects running that month.
            budget_active: total budget of active projects.
            n_projects_started: projects that started that month.
            n_projects_finished: projects that finished that month (i.e. no
                longer active, the month after their end_date).
    """
    dept_cols = ["department", "faculty"]

    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    current_month = pd.Timestamp.today().to_period("M")

    # Month of start/end; a project stays active through its end_month and
    # is only "finished" the following month. Cap at current month, no future.
    df["start_month"] = df["start_date"].dt.to_period("M")
    df["end_month"] = df["end_date"].dt.to_period("M").clip(upper=current_month)
    df["finished_month"] = (df["end_date"].dt.to_period("M") + 1).clip(
        upper=current_month
    )

    # Expand each project into one row per active month
    df["months_active"] = df.apply(
        lambda r: pd.period_range(r["start_month"], r["end_month"], freq="M"), axis=1
    )
    active = df.explode("months_active").rename(columns={"months_active": "month"})

    # Summaries of active projects and switching active/non-active
    active_summary = (
        active.groupby(["month", *dept_cols])
        .agg(n_projects_active=("pk", "count"), budget_active=("budget", "sum"))
        .reset_index()
    )
    started_summary = (
        df.groupby(["start_month", *dept_cols])
        .agg(n_projects_started=("pk", "count"))
        .reset_index()
        .rename(columns={"start_month": "month"})
    )
    finished_summary = (
        df.groupby(["finished_month", *dept_cols])
        .agg(n_projects_finished=("pk", "count"))
        .reset_index()
        .rename(columns={"finished_month": "month"})
    )

    # Outer-merge so only months with activity, a start, or a finish appear
    result = active_summary.merge(
        started_summary, on=["month", *dept_cols], how="outer"
    ).merge(finished_summary, on=["month", *dept_cols], how="outer")
    result = result[result["month"] <= current_month]

    # Some cleaning and reorganisation
    count_cols = ["n_projects_active", "n_projects_started", "n_projects_finished"]
    result[count_cols] = result[count_cols].fillna(0).astype(int)
    result["budget_active"] = result["budget_active"].fillna(0.0)
    result["month"] = result["month"].astype(str)

    result = result.sort_values(["department", "month"]).reset_index(drop=True)
    cols = [
        "month",
        "faculty",
        "department",
        "n_projects_active",
        "budget_active",
        "n_projects_started",
        "n_projects_finished",
    ]
    return result[cols]


@api.get("/data/projects.csv")
def get_projects_csv_file(request: HttpRequest) -> HttpResponse:
    """Return a CSV file with all projects information.

    The file contains the number of projects and budget for each
    department broken down by month, with columns indicating projects
    that stated that month and projects that ended.

    Args:
        request: The HTTP request.

    Returns:
        A CSV file to download.
    """
    data = _assemble_projects_summary()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users.csv"'

    data.to_csv(response)

    return response
