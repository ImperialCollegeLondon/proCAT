"""Tests for the report module."""

from datetime import date, datetime, timedelta
from http import HTTPStatus
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_get_actual_chargeable_days(user, project):
    """Test the get_actual_chargeable_days function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    # Check when there are no time entries
    assert report.get_actual_chargeable_days(project, start_date, end_date) == (
        None,
        None,
    )

    # Create time entries
    time_entry_A = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 30),
        end_time=datetime(2025, 6, 2, 12, 30),
    )  # 3 hours total
    time_entry_B = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 4, 10, 0),
        end_time=datetime(2025, 6, 4, 14, 0),
    )  # 4 hours total

    pks = [time_entry_A.pk, time_entry_B.pk]
    expected_result = (1, pks)  # 7 hours total = 1 day
    assert (
        report.get_actual_chargeable_days(project, start_date, end_date)
        == expected_result
    )


@pytest.mark.django_db
def test_get_valid_funding_sources(project, analysis_code):
    """Test the get_valid_funding_sources function."""
    from main import models, report

    end_date = datetime.now().date() + timedelta(days=14)

    # Create expired funding
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date - timedelta(10),
        budget=1000.00,
        daily_rate=1000.00,
    )
    # Create valid funding
    valid_funding = models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G56789",
        analysis_code=analysis_code,
        expiry_date=end_date + timedelta(10),
        budget=1000.00,
        daily_rate=1000.00,
    )
    # TODO: Create depleted funding when effort_left implemented

    assert report.get_valid_funding_sources(project, end_date) == [valid_funding]


@pytest.mark.django_db
def test_create_pro_rata_monthly_charges(department, user, analysis_code):
    """Test the create_pro_rata_monthly_charges function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 15)

    # Create project and funding with Pro-rata charging
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
        budget=1000.00,
        daily_rate=100.00,
    )

    # Create Pro-rata charge and check amount
    report.create_pro_rata_monthly_charges(project, start_date, end_date)
    expected_amount = models.MonthlyCharge.objects.get(date=start_date).amount
    assert funding.monthly_pro_rata_charge == expected_amount


@pytest.mark.django_db
def test_create_actual_monthly_charges_validate_effort_left(
    department, user, analysis_code
):
    """Test the create_actual_monthly_charges function when charge exceeds total effort.

    TODO: Update this to be more sensible when funding.effort_left implemented.
    """
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    # Create project and time entry that will exceed funding budget
    project = models.Project.objects.create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=start_date,
        end_date=end_date,
        status="Active",
        charging="Actual",
    )
    models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date,
        budget=1000.00,
        daily_rate=1000.00,
    )  # Only 1 day worth of funding
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 1, 1, 0),
        end_time=datetime(2026, 6, 1, 1, 0),
    )  # 1 year total

    # Check that the time entry exceeds 1 day
    with pytest.raises(
        ValidationError,
        match=(
            "Total chargeable days exceeds the total effort left for project "
            f"{project.name}."
        ),
    ):
        report.create_actual_monthly_charges(project, start_date, end_date)


@pytest.mark.django_db
def test_create_actual_monthly_charges(department, user, analysis_code):
    """Test the create_actual_monthly_charges function.

    TODO: Update when funding.effort_left implemented to test charges are created for
    multiple funding sources.
    """
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
    funding_A = models.Funding.objects.create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=end_date,  # expires first
        budget=1000.00,
        daily_rate=100.00,
    )
    funding_B = models.Funding.objects.create(  # noqa: F841
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G56789",
        analysis_code=analysis_code,
        expiry_date=end_date + timedelta(30),
        budget=5000.00,
        daily_rate=500.00,
    )

    # Check no monthly charge is created if there are no time entries
    report.create_actual_monthly_charges(project, start_date, end_date)
    assert not models.MonthlyCharge.objects.exists()

    time_entry_A = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 0),
        end_time=datetime(2025, 6, 2, 16, 0),
    )  # 7 hours total
    time_entry_B = models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 4, 10, 0),
        end_time=datetime(2025, 6, 4, 13, 30),
    )  # 3.5 hours total

    # Create monthly charges
    report.create_actual_monthly_charges(project, start_date, end_date)

    # Calculate the chargeable days from the time entries
    chargeable_hours = 0
    for time_entry in [time_entry_A, time_entry_B]:
        chargeable_hours += (
            time_entry.end_time - time_entry.start_time
        ).total_seconds() / 3600
    chargeable_days = chargeable_hours / 7

    # Check monthly charge created against funding A
    charge = models.MonthlyCharge.objects.get(date=start_date)
    assert round(funding_A.daily_rate * chargeable_days, 2) == charge.amount

    # Check monthly charge has been added to time entries
    assert charge in time_entry_A.monthly_charge.all()


@pytest.mark.django_db
def test_get_csv_charges_block(project, funding):
    """Test the get_csv_charges_block function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    charge = models.MonthlyCharge.objects.create(
        date=start_date,
        project=project,
        funding=funding,
        amount=10.00,
    )
    expected_block = [
        [
            charge.funding.cost_centre,
            charge.funding.activity,
            charge.funding.analysis_code.code,
            f"{charge.amount:.2f}",
            charge.description,
        ]
    ]
    assert expected_block == report.get_csv_charges_block(start_date)


def test_get_csv_header_block(project, funding):
    """Test the get_csv_header_block function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    charge = models.MonthlyCharge.objects.create(
        date=start_date, project=project, funding=funding, amount=10
    )
    amount = f"{charge.amount:.2f}"

    expected_block = [
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
        ["Journal Amount", amount, "", "", ""],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Credit", "Line Description"],
        [
            "ITPP",
            "G80410",
            "162104",
            amount,
            f"RSE Projects: {charge.date.strftime('%B %Y')}",
        ],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Debit", "Line Description"],
    ]
    assert expected_block == report.get_csv_header_block(start_date)


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


def test_invalid_date_create_charges_report():
    """Test that a future date raises an error for create_charges_report."""
    from main import report

    current_date = datetime.now().date()
    future_date = current_date + timedelta(40)
    writer = Mock()

    with pytest.raises(ValidationError, match="Report date must not be in the future."):
        report.create_charges_report(future_date.month, future_date.year, writer)


@pytest.mark.django_db
def test_create_charges_report_for_download(department, user, analysis_code):
    """Test the create_charges_report_for_download function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    # Create time entry for monthly charge
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
        budget=10000.00,
        daily_rate=100.00,
    )
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 0),
        end_time=datetime(2025, 6, 2, 12, 30),
    )  # 3.5 hours total (0.5 days)

    response = report.create_charges_report_for_download(
        start_date.month, start_date.year
    )
    expected_fname = f"charges_report_{start_date.month}-{start_date.year}.csv"

    # Check HTTP response for CSV download
    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"] == "text/csv"
    assert expected_fname in response["Content-Disposition"]

    n_days = 0.5
    expected_charge_row = ",".join(
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

    # Check the charge row in the CSV is as expected
    assert expected_charge_row in response.content.decode("utf-8")


@pytest.mark.django_db
def test_create_charges_report_for_attachment(department, user, analysis_code):
    """Test the create_charges_report_for_attachment function."""
    from main import models, report

    start_date = date(2025, 6, 1)
    end_date = date(2025, 7, 1)

    # Create time entry for monthly charge
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
        budget=10000.00,
        daily_rate=100.00,
    )
    models.TimeEntry.objects.create(
        user=user,
        project=project,
        start_time=datetime(2025, 6, 2, 9, 0),
        end_time=datetime(2025, 6, 2, 12, 30),
    )  # 3.5 hours total (0.5 days)

    n_days = 0.5
    csv_string = report.create_charges_report_for_attachment(6, 2025)
    expected_charge_row = (
        f"{funding.cost_centre},{funding.activity},{funding.analysis_code.code},"
        f"{funding.daily_rate * n_days:.2f},"
        f"RSE Project {project.name} ({funding.cost_centre}_"
        f"{funding.activity}): 6/2025 [rcs-manager@imperial.ac.uk]\r\n"
    )

    # Check the charge row in the CSV is as expected
    assert expected_charge_row in csv_string
