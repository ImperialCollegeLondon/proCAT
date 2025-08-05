"""Report for including all the charges to be expensed for the month."""

import csv
import io
from _csv import Writer
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse

from . import models, utils
from .models import Funding, Project


def get_actual_chargeable_days(
    project: Project, start_date: date, end_date: date
) -> tuple[Decimal, list[int]] | tuple[None, None]:
    """Get the number of chargeable days for projects with Actual charging.

    Args:
        project: the Project for charging
        start_date: the start date for the charging period
        end_date: the end date for the charging period

    Returns:
        A tuple of the number of chargeable days and list of pks of relevant time
            entries, or a tuple of None values if there are no time entries.
    """
    start_time = datetime.combine(start_date, datetime.min.time())
    end_time = datetime.combine(end_date, datetime.min.time())

    time_entries = models.TimeEntry.objects.filter(
        project=project,
        start_time__gte=start_time,
        start_time__lt=end_time,
        monthly_charge__isnull=True,
    )
    pks = list(time_entries.values_list("pk", flat=True))

    if len(time_entries) == 0:
        return None, None

    hours, _ = utils.get_logged_hours(time_entries)
    total_days = Decimal(str(round(hours / 7, 1)))
    return total_days, pks


def get_valid_funding_sources(project: Project, end_date: date) -> list[Funding]:
    """Get valid funding sources."""
    funding_sources = list(
        project.funding_source.all()
        .filter(
            expiry_date__gte=end_date,
        )
        .order_by("expiry_date")
    )
    funding_sources = [
        funding for funding in funding_sources if funding.funding_left > 0
    ]
    return funding_sources


def create_pro_rata_monthly_charges(
    project: Project, start_date: date, end_date: date
) -> None:
    """Create monthly charges for projects with Pro-rata charging.

    As the charge is constant and based on project duration and budget, this function
    does not check if the charge exceeds total funding.

    Args:
        project: the Project for charging
        start_date: the start date for the charging period
        end_date: the end date for the charging period
    """
    funding_sources = get_valid_funding_sources(project, end_date)

    for funding in funding_sources:
        if not funding.monthly_pro_rata_charge:
            continue

        charge = models.MonthlyCharge.objects.create(
            project=project,
            funding=funding,
            amount=funding.monthly_pro_rata_charge,
            date=start_date,
        )
        charge.clean()
        charge.save()


def create_actual_monthly_charges(
    project: Project, start_date: date, end_date: date
) -> None:
    """Create monthly charges for projects with Actual charging.

    Args:
        project: the Project for charging
        start_date: the start date for the charging period
        end_date: the end date for the charging period
    """
    total_days, pks = get_actual_chargeable_days(project, start_date, end_date)

    if total_days and project.days_left:
        if total_days > project.days_left[0]:
            raise ValidationError(
                "Total chargeable days exceeds the total effort left "
                f"for project {project.name}."
            )

        # create a monthly charge for each funding source
        funding_sources = get_valid_funding_sources(project, end_date)
        for funding in funding_sources:
            if total_days <= 0:  # we are done charging
                break

            days_deduce = min(total_days, funding.effort_left)
            amount = round(days_deduce * funding.daily_rate, 1)
            charge = models.MonthlyCharge.objects.create(
                project=project, funding=funding, amount=amount, date=start_date
            )
            charge.clean()
            charge.save()
            total_days -= days_deduce

            # update time entries with monthly charge
            for time_entry in models.TimeEntry.objects.filter(pk__in=pks):
                time_entry.monthly_charge.add(charge)


def get_csv_charges_block(start_date: date) -> list[list[str]]:
    """Get the charges block for the CSV report.

       Contains the data for each row in the charges block, representing individual
       monthly charges for the month.

    Args:
        start_date: starting date (1st of the  month) for the report period

    Returns:
        A list of lists representing rows in the csv for each charge.
    """
    fields = [
        "funding__cost_centre",
        "funding__activity",
        "funding__analysis_code__code",
        "amount",
        "description",
    ]
    queryset = models.MonthlyCharge.objects.filter(date=start_date).values(*fields)
    charges_block = []
    for record in queryset:
        charges_block.append([str(record[field]) for field in fields])
    return charges_block


def get_csv_header_block(start_date: date) -> list[list[str]]:
    """Get the header blocks for the CSV report.

    Aggregates the total charge for the month across all monthly charges.

    Args:
        start_date: starting date (1st of the  month) for the report period

    Returns:
        A list of lists representing the 'header' rows in the CSV, excluding the rows
            that include information on individual monthly charges
    """
    amount = models.MonthlyCharge.objects.filter(date=start_date).aggregate(
        Sum("amount")
    )["amount__sum"]
    if amount:
        amount = f"{amount:.2f}"

    header_block = [
        ["Journal Name", f"RCS_MANAGER RSE {start_date.strftime('%Y-%m')}", "", "", ""],
        [
            "Journal Description",
            f"RCS RSE Recharge for {start_date.strftime('%Y-%m')}",
            "",
            "",
            "",
        ],
        ["Journal Amount", str(amount), "", "", ""],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Credit", "Line Description"],
        [
            "ITPP",
            "G80410",
            "162104",
            f"{amount}",
            f"RSE Projects: {start_date.strftime('%B %Y')}",
        ],
        ["", "", "", "", ""],
        ["Cost Centre", "Activity", "Analysis", "Debit", "Line Description"],
    ]
    return header_block


def write_to_csv(
    header_block: list[list[str]],
    charges_block: list[list[str]],
    writer: Writer,
) -> None:
    """Write CSV rows using CSV writer object.

    Args:
        header_block: list of lists representing rows in the CSV report for the header
            blocks
        charges_block: list of lists representing rows in the CSV report for the charges
            block
        writer: csv writer object
    """
    for block in [header_block, charges_block]:
        for row in block:
            writer.writerow(row)


def create_charges_report(month: int, year: int, writer: Writer) -> None:
    """Generate the CSV report by creating Monthly Charge objects and writing to a CSV.

    Args:
        month: month for the report date
        year: year for the report date
        writer: csv.writer to create the CSV report as HttpResponse or StringIO
    """
    # get the start_date and end dates (as the 1st of the month)
    start_date = date(year, month, 1)
    if start_date > datetime.today().date():
        raise ValidationError("Report date must not be in the future.")
    end_date = (start_date + timedelta(days=31)).replace(day=1)

    # delete existing Pro-rata and Actual charges so they can be re-created
    models.MonthlyCharge.objects.filter(date=start_date).exclude(
        project__charging="Manual"
    ).delete()

    # get all Pro-rata and Actual projects that overlap with this time period
    projects = models.Project.objects.filter(
        start_date__lt=end_date,
        end_date__gte=start_date,
        start_date__isnull=False,
        end_date__isnull=False,
    ).exclude(charging="Manual")

    for project in projects:
        if project.charging == "Pro-rata":
            create_pro_rata_monthly_charges(project, start_date, end_date)
        elif project.charging == "Actual":
            create_actual_monthly_charges(project, start_date, end_date)

    header_block = get_csv_header_block(start_date)
    charges_block = get_csv_charges_block(start_date)
    write_to_csv(header_block, charges_block, writer)


def create_charges_report_for_download(month: int, year: int) -> HttpResponse:
    """Create the charges report as a HTTPResponse for download from the web app.

    Args:
        month: month for the report date
        year: year for the report date

    Returns:
        HttpResponse for the CSV report to download.
    """
    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": "attachment; "
            f"filename=charges_report_{month}-{year}.csv"
        },
    )
    writer = csv.writer(response)
    create_charges_report(month, year, writer)
    return response


def create_charges_report_for_attachment(month: int, year: int) -> str:
    """Create the charges report with StringIO to be attached to an email.

    Args:
        month: month for the report date
        year: year for the report date

    Returns:
        String representing the charges report.
    """
    csv_file = io.StringIO()
    writer = csv.writer(csv_file)
    create_charges_report(month, year, writer)
    return csv_file.getvalue()
