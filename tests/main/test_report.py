"""Tests for the report module."""

from datetime import date, datetime
from http import HTTPStatus
from unittest.mock import Mock

import pytest


def test_get_pro_rata_charges():
    """Test the get_pro_rata_charges function."""
    from main import models, report

    project = models.Project(
        name="ProCAT", start_date=date(2025, 6, 3), end_date=date(2025, 6, 26)
    )

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)
    assert report.get_pro_rata_charges(project, start_date, end_date) == 17


@pytest.mark.django_db
def test_get_actual_charges(user, project):
    """Test the get_actual_charges function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)
    assert report.get_actual_charges(project, start_date, end_date) == (None, None)

    time_entry_A = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 30),
        end_time=datetime(2025, 6, 2, 12, 30),
    )
    time_entry_B = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 4, 10, 0),
        end_time=datetime(2025, 6, 4, 14, 0),
    )
    pks = [time_entry_A.pk, time_entry_B.pk]
    assert report.get_actual_charges(project, start_date, end_date) == (1, pks)


@pytest.mark.django_db
def test_create_monthly_charges_pro_rata(department, user, analysis_code):
    """Test the create_monthly_charges function with pro-rata charging."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)
    num_working_days = 21

    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=start_date,
        end_date=end_date,
        status="Active",
        charging="Pro-rata",
    )
    funding = models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date,
        budget=2100.00,
        daily_rate=100.00,
    )

    report.create_monthly_charges(project, start_date, end_date)
    charge = models.MonthlyCharge.objects.get(date=start_date)
    assert charge.amount == funding.daily_rate * num_working_days


@pytest.mark.django_db
def test_create_monthly_charges_actual(department, user, analysis_code):
    """Test the create_monthly_charges function with actual charging."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=start_date,
        end_date=end_date,
        status="Active",
        charging="Actual",
    )
    funding = models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date,
        budget=2100.00,
        daily_rate=100.00,
    )
    time_entry_A = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 0),
        end_time=datetime(2025, 6, 2, 16, 0),
    )
    time_entry_B = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 4, 10, 0),
        end_time=datetime(2025, 6, 4, 13, 30),
    )
    hours = 0
    for time_entry in [time_entry_A, time_entry_B]:
        hours += (time_entry.end_time - time_entry.start_time).total_seconds() / 3600
    days = hours / 7

    report.create_monthly_charges(project, start_date, end_date)
    charge = models.MonthlyCharge.objects.get(date=start_date)
    assert charge.amount == funding.daily_rate * days


@pytest.mark.django_db
def test_get_csv_charges_block(project, funding):
    """Test the get_csv_charges_block."""
    from main import models, report

    start_date = datetime.now().date()
    charge = models.MonthlyCharge.objects.create(
        date=start_date,
        project=project,
        funding=funding,
        amount=10.00,
    )
    block = [
        [
            charge.funding.cost_centre,
            charge.funding.activity,
            charge.funding.analysis_code.code,
            f"{charge.amount:.2f}",
            charge.description,
        ]
    ]
    assert block == report.get_csv_charges_block(start_date)


def test_get_csv_header_block(project, funding):
    """Test the get_csv_header_block function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    charge = models.MonthlyCharge.objects.create(
        date=start_date, project=project, funding=funding, amount=10
    )

    block = [
        [
            "Journal Name",
            f"RCS_MANAGER RSE {charge.date.strftime('%Y-%m')}",
            "",
            "",
            "",
        ],
        [
            "Journal Description",
            f"RCS RSE Recharge for {charge.date.strftime('%Y-%m')}",
            "",
            "",
            "",
        ],
        ["Journal Amount", str(charge.amount), "", "", ""],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Credit", "Line Description"],
        [
            "ITPP",
            "G80410",
            "162104",
            f"{charge.amount},RSE Projects: {charge.date.strftime('%B %Y')}",
        ],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Debit", "Line Description"],
    ]

    assert block == report.get_csv_header_block(start_date)


def test_write_to_csv():
    """Test the write_to_csv function."""
    from main import report

    header_block = [
        [
            "Journal Name",
            "RCS_MANAGER RSE 2025-07",
            "",
            "",
            "",
        ],
    ]
    charges_block = [
        ["Cost Centre", "Activity", "Analysis", "Debit", "Line Description"],
        [
            "AAA",
            "G12345",
            "5678",
            "100.00",
            "RSE Project ProCAT (AAA_1234): 7/2025 [rcs-manager@imperial.ac.uk",
        ],
    ]

    writer = Mock()
    report.write_to_csv(header_block, charges_block, writer)
    writer.writerow.assert_any_call(header_block[0])
    writer.writerow.assert_any_call(charges_block[0])
    writer.writerow.assert_any_call(charges_block[1])


@pytest.mark.django_db
def test_create_charges_report(department, user, analysis_code):
    """Test the create_charges_report function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=start_date,
        end_date=end_date,
        status="Active",
        charging="Actual",
    )
    funding = models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date,
        budget=2100.00,
        daily_rate=100.00,
    )
    time_entry = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 0),
        end_time=datetime(2025, 6, 2, 12, 30),
    )
    n_days = (time_entry.end_time - time_entry.start_time).seconds / 3600 / 7
    response = report.create_charges_report(6, 2025)
    fname = "cost_report_6-2025.csv"

    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"] == "text/csv"
    assert fname in response["Content-Disposition"]

    charge_row = ",".join(
        [
            funding.cost_centre,
            funding.activity,
            funding.analysis_code.code,
            f"{funding.daily_rate * n_days:.2f}",
            (
                f"RSE Project {project.name} ({funding.cost_centre}_"
                f"{funding.activity}): 6/2025 [rcs-manager@imperial.ac.uk]"
            ),
        ]
    )
    assert charge_row in response.content.decode("utf-8")
