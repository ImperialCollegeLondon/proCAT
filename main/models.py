"""Models module for main app."""

from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from procat.settings.settings import (
    EFFORT_LEFT_THRESHOLD,
    WEEKS_LEFT_THRESHOLD,
    WORKING_DAYS,
)


class User(AbstractUser):
    """Custom user model."""

    pass


class Department(models.Model):
    """Model to manage the departments.

    You can find the faculties and potential departments in:

    https://www.imperial.ac.uk/faculties-and-departments/
    """

    _FACULTY = (
        ("Faculty of Engineering", "Faculty of Engineering"),
        ("Faculty of Medicine", "Faculty of Medicine"),
        ("Faculty of Natural Sciences", "Faculty of Natural Sciences"),
        ("Imperial Business School", "Imperial Business School"),
        ("Other", "Other"),
    )

    name = models.CharField(
        "Department",
        unique=True,
        blank=False,
        null=False,
        help_text="Name of the department, centre or school.",
    )

    faculty = models.CharField(
        "Faculty",
        blank=False,
        null=False,
        choices=_FACULTY,
        help_text="Faculty the department belongs to.",
    )

    def __str__(self) -> str:
        """String representation of the Department object."""
        return f"{self.name} - {self.faculty}"


class AnalysisCode(models.Model):
    """Analysis code to use during charging."""

    code = models.IntegerField(
        "Code",
        unique=True,
        blank=False,
        null=False,
        help_text="Code for the analysis to use during charging.",
    )
    description = models.CharField(
        "Description",
        unique=True,
        blank=False,
        null=False,
        help_text="Description of the code.",
    )
    notes = models.TextField(
        "Notes",
        blank=False,
        null=False,
        help_text="Longer explanation about when to use the code.",
    )

    def __str__(self) -> str:
        """String representation of the Analysis Code object."""
        return f"{self.code} - {self.description}"


class Project(models.Model):
    """Software project details."""

    _NATURE = (("Support", "Support"), ("Standard", "Standard"))
    _STATUS = (
        ("Tentative", "Tentative"),
        ("Confirmed", "Confirmed"),
        ("Active", "Active"),
        ("Finished", "Finished"),
        ("Not done", "Not done"),
    )
    _CHARGING = (
        ("Actual", "Actual"),
        ("Pro-rata", "Pro-rata"),
        ("Manual", "Manual"),
    )

    name = models.CharField(
        "Name",
        unique=True,
        blank=False,
        null=False,
        help_text="Name of the project.",
    )
    nature = models.CharField(
        "Nature",
        blank=False,
        null=False,
        choices=_NATURE,
        help_text="Nature of the project.  Typically, support projects cannot be "
        "allocated to sprints easily, the work there is more lightweight and ad hoc, "
        "sometimes at short notice.",
    )
    pi = models.CharField(
        "Principal Investigator",
        blank=False,
        null=False,
        help_text="Name of the principal investigator responsible for the project. "
        "It should be the actual grant holder, not the main point of contact",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        blank=False,
        null=False,
        help_text="The department in which the research project is based, primarily.",
    )
    start_date = models.DateField(
        "Start date", null=True, blank=True, help_text="Start date for the project."
    )
    end_date = models.DateField(
        "End date", null=True, blank=True, help_text="End date for the project."
    )
    lead = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Project lead from the RSE side.",
    )
    status = models.CharField(
        "Status",
        blank=False,
        null=False,
        default="Tentative",
        choices=_STATUS,
        help_text="Status of the project. Unless the status is 'Tentative' or "
        "'Not done', most other fields are mandatory.",
    )
    charging = models.CharField(
        "Charging method",
        blank=False,
        null=False,
        default="Actual",
        choices=_CHARGING,
        help_text="Method for charging the costs of the project. 'Actual' is based"
        " on timesheet records. 'Pro-rata' charges the same amount every month. "
        "Finally, in 'Manual' the charges are scheduled manually.",
    )
    notifications_effort = models.JSONField(
        "Summary of effort left notifications",
        default=dict,
        blank=True,
        help_text="Summarises the notifications sent when an effort threshold "
        "is crossed and the corresponding dates.",
    )
    notifications_weeks = models.JSONField(
        "Summary of weeks left notifications",
        default=dict,
        blank=True,
        help_text="Summarises the notifications sent when the weeks threshold "
        "is crossed and the corresponding dates.",
    )
    clockify_id = models.CharField(
        "Clockify ID",
        blank=True,
        null=False,
        help_text="The ID of the project in Clockify, if applicable.",
    )

    def __str__(self) -> str:
        """String representation of the Project object."""
        return self.name

    def clean(self) -> None:
        """Ensure all fields have a value unless status is 'Tentative' or 'Not done'.

        It also checks that, if present, the end date is after the start date.
        """
        if self.status == "Tentative" or self.status == "Not done":
            return super().clean()

        if not self.start_date or not self.end_date or not self.lead:
            raise ValidationError(
                "All fields are mandatory except if Project status is 'Tentative' or "
                "'Not done'."
            )

        if self.end_date <= self.start_date:
            raise ValidationError("The end date must be after the start date.")

        if self.pk is not None and self.status in ("Active", "Confirmed"):
            if not self.funding_source.exists():
                raise ValidationError(
                    "Active and Confirmed projects must have at least 1 funding source."
                )

            if not all([f.is_complete() for f in self.funding_source.all()]):
                raise ValidationError(
                    "Funding of Active and Confirmed projects must be complete."
                )

    @property
    def weeks_to_deadline(self) -> tuple[int, float] | None:
        """Provide the number of weeks left until project deadline.

        Only relevant for active projects.

        Returns:
            The number of weeks left or None if the project is Tentative or Not done.
        """
        if self.status in ["Active", "Confirmed"] and self.end_date and self.start_date:
            left = (self.end_date - timezone.now().date()).days / 7
            total = (self.end_date - self.start_date).days / 7
            return int(left), round(left / total * 100, 1)

        return None

    @property
    def total_effort(self) -> float | None:
        """Provide the total days worth of effort available from funding.

        Returns:
            The total number of days effort, or None if there is no funding information.
        """
        if self.funding_source.exists():
            total = sum([funding.effort for funding in self.funding_source.all()])
            return total

        return None

    @property
    def total_funding_left(self) -> Decimal | None:
        """Provide the total funding left after deducting confirmed charges.

        Returns:
            The total monetary amount of funding left, or none if there is no funding
            information.
        """
        if self.funding_source.exists():
            total = sum(
                [funding.funding_left for funding in self.funding_source.all()],
                Decimal(0),
            )
            return total

        return None

    @property
    def percent_effort_left(self) -> float | None:
        """Provide the percentage of effort left.

        Returns:
            The percentage of effort left, or None if there is no funding information.
        """
        if left := self.days_left:
            return left[1]
        return None

    @property
    def days_left(self) -> tuple[float, float] | None:
        """Provide the days worth of effort left.

        Returns:
            The number of days and percentage worth of effort left, or None if there is
            no funding information.
        """
        from .utils import get_logged_hours

        if self.total_effort:
            time_entries = self.timeentry_set.all()
            hours_logged = get_logged_hours(time_entries)[0]
            left = self.total_effort - (hours_logged / 7)
            return round(left, 1), round(left / self.total_effort * 100, 1)

        return None

    def check_and_notify_status(self) -> None:
        """Check the project status and notify accordingly."""
        from .tasks import notify_left_threshold

        check = False

        assert self.lead and hasattr(self.lead, "email")

        for threshold in sorted(EFFORT_LEFT_THRESHOLD):
            if self.percent_effort_left is None or self.percent_effort_left > threshold:
                continue

            if str(threshold) in self.notifications_effort:
                # Already notified for this threshold in the past
                break

            notify_left_threshold(
                email=self.lead.email,
                lead=self.lead.get_full_name(),
                project_name=self.name,
                threshold_type="effort",
                threshold=threshold,
                value=self.days_left[0] if self.days_left else 0,
            )
            self.notifications_effort[str(threshold)] = (
                timezone.now().date().isoformat()
            )
            check = True
            break

        for threshold in sorted(WEEKS_LEFT_THRESHOLD):
            if self.weeks_to_deadline is None or self.weeks_to_deadline[1] > threshold:
                continue

            if str(threshold) in self.notifications_weeks:
                # Already notified for this threshold in the past
                break

            notify_left_threshold(
                email=self.lead.email,
                lead=self.lead.get_full_name(),
                project_name=self.name,
                threshold_type="weeks",
                threshold=threshold,
                value=self.weeks_to_deadline[0] if self.weeks_to_deadline else 0,
            )
            self.notifications_weeks[str(threshold)] = timezone.now().date().isoformat()
            check = True
            break

        if check:
            self.save(update_fields=["notifications_effort", "notifications_weeks"])

    @property
    def total_working_days(self) -> int | None:
        """Provide the total number of working (business) days given the dates.

        Returns:
            Number of working days between the project start and end date.
        """
        if self.start_date and self.end_date:
            days = (self.end_date - self.start_date).days
            return round((days / 365) * WORKING_DAYS)
        return None

    @property
    def effort_per_day(self) -> float | None:
        """Calculate the estimated effort per day.

        Considers only working (business) days.

        Returns:
            Float representing the estimated effort per day over project lifespan.
        """
        if self.total_effort and self.total_working_days:
            return self.total_effort / self.total_working_days
        return None


class Funding(models.Model):
    """Funding associated with a project."""

    _SOURCES = (("Internal", "Internal"), ("External", "External"))

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="The project that the funding relates to.",
        related_name="funding_source",
    )

    source = models.CharField(
        "Source",
        blank=False,
        null=False,
        choices=_SOURCES,
        help_text="'Internal' refers to projects from within ICT or community"
        " projects. If not 'Internal', all fields are mandatory.",
    )

    funding_body = models.CharField(
        "Funding body",
        blank=True,
        null=True,
        help_text="The organisation or department providing the funding.",
    )

    cost_centre = models.CharField(
        "Cost centre",
        blank=True,
        null=True,
        help_text="The cost centre for the project.",
    )

    activity = models.CharField(
        "activity",
        blank=True,
        null=True,
        help_text="The activity code designated to the project, 6 alphanumeric"
        " characters starting with P, F, G or I.",
    )

    analysis_code = models.ForeignKey(
        AnalysisCode,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="The analysis code to use for charging.",
    )

    expiry_date = models.DateField(
        "Expiry date",
        null=True,
        blank=True,
        help_text="Account expiry date, meaning the latest that charges can be made to"
        " the account.",
    )

    budget = models.DecimalField(
        "Budget",
        blank=False,
        null=False,
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="The total budget for the funding.",
    )

    daily_rate = models.DecimalField(
        "Daily rate",
        default=389.00,
        blank=False,
        null=False,
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="The current daily rate, which defaults to 389.00.",
    )

    class Meta:
        """Meta class for the model."""

        verbose_name_plural = "funding"

    def __str__(self) -> str:
        """String representation of the Funding object."""
        return f"{self.project} - £{self.budget:.2f} - {self.project_code}"

    def clean(self) -> None:
        """Ensure that the activity code has a valid value."""
        if (
            self.project
            and self.project.status in ("Active", "Confirmed")
            and not self.is_complete()
        ):
            raise ValidationError(
                "Funding of Active and Confirmed projects must be complete."
            )

        allowed_characters = ["P", "F", "G", "I"]
        if self.activity and (
            len(self.activity) != 6
            or not self.activity.isalnum()
            or self.activity[0] not in allowed_characters
        ):
            raise ValidationError(
                "Activity code must be 6 alphanumeric characters starting with P, F, "
                "G or I."
            )

    def is_complete(self) -> bool:
        """Checks if funding record is complete.

        This is only relevant to funding where source is external.
        """
        if self.source == "Internal":
            return True

        return bool(
            self.funding_body
            and self.cost_centre
            and self.activity
            and self.analysis_code
            and self.expiry_date
        )

    @property
    def project_code(self) -> str:
        """Provide the project code, containing the cost centre and activity code.

        Returns:
            The designated project code.
        """
        if self.cost_centre and self.activity:
            return f"{self.cost_centre}_{self.activity}"

        return "None"

    @property
    def effort(self) -> float:
        """Provide the effort in days, calculated based on the budget and daily rate.

        Returns:
            The total number of days of effort provided by the funding.
        """
        days_effort = round(self.budget / self.daily_rate, 1)
        return float(days_effort)

    @property
    def funding_left(self) -> Decimal:
        """Provide the funding left in currency.

        Funding left is calculated based on 'Confirmed' monthly charges.

        Returns:
            The amount of funding left.
        """
        funding_spent = MonthlyCharge.objects.filter(
            funding=self, status="Confirmed"
        ).aggregate(Sum("amount"))["amount__sum"]
        if funding_spent:
            return self.budget - funding_spent
        return self.budget

    @property
    def effort_left(self) -> float:
        """Provide the effort left in days.

        Returns:
            The number of days worth of effort left.
        """
        return float(round(self.funding_left / self.daily_rate, 1))

    @property
    def monthly_pro_rata_charge(self) -> float | None:
        """Calculate the charge per month if the project has Pro-rata charging.

        Calculates the number of months between project start and end date regardless
        of the day of the month so the monthly charge will be the same regardless
        of the number of days in the month.
        """
        if (
            self.project.charging == "Pro-rata"
            and self.project.start_date
            and self.project.end_date
        ):
            months = (
                (self.project.end_date.year - self.project.start_date.year) * 12
                + (self.project.end_date.month - self.project.start_date.month)
                + 1
            )
            return float(self.budget / months)
        return None


class Capacity(models.Model):
    """Proportion of working time that team members are able to work on projects."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text="The team member this capacity relates to.",
    )

    value = models.DecimalField(
        "Capacity",
        default=0.7,
        blank=False,
        null=False,
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Capacity fraction of 1 FTE devoted to project work.",
    )

    start_date = models.DateField(
        "Start date",
        null=False,
        blank=False,
        help_text="The date from when this capacity applies.",
    )

    class Meta:
        """Meta class for the model."""

        verbose_name_plural = "capacities"

    def __str__(self) -> str:
        """String representation of the Capacity object."""
        return f"From {self.start_date}, the capacity of {self.user} is {self.value}."


class MonthlyCharge(models.Model):
    """Monthly charge for a specific project, account and analysis code."""

    _STATUS_CHOICES = (("Draft", "Draft"), ("Confirmed", "Confirmed"))

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text="The project the monthly charge relates to.",
    )

    funding = models.ForeignKey(
        Funding,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text="The funding source to be used for the charge.",
    )

    amount = models.DecimalField(
        "Amount",
        blank=False,
        null=False,
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="The amount to be charged to the funding source.",
    )

    date = models.DateField(
        "Charge date",
        null=False,
        blank=False,
        help_text="The date the charges related to (the month previous).",
    )

    description = models.CharField(
        "Description",
        null=False,
        blank=True,
        help_text="Line description displayed in the charges report. Mandatory for "
        "manually charged projects.",
    )

    status = models.CharField(
        "Status",
        max_length=20,
        choices=_STATUS_CHOICES,
        default="Draft",
        blank=False,
        null=False,
        help_text="The status of the monthly charge ('Draft' or 'Confirmed'). Confirmed"
        " monthly charges are not deleted.",
    )

    def __str__(self) -> str:
        """String representation of the MonthlyCharge object."""
        return self.description

    def clean(self) -> None:
        """Ensure the charge has valid funding attached and description if Manual."""
        super().clean()
        if not self.funding.expiry_date:
            raise ValidationError("Funding source must have an expiry date.")

        if (
            self.date > self.funding.expiry_date
            or self.funding.funding_left < 0  # After deducting charge amount
        ):
            raise ValidationError(
                "Monthly charge must not exceed the funding date or amount."
            )

        if self.project.charging == "Manual":
            if not self.description:
                raise ValidationError(
                    "Line description needed for manual charging method."
                )
        else:
            self.description = (
                f"RSE Project {self.project} ({self.funding.project_code}): "
                f"{self.date.month}/{self.date.year} [rcs-manager@imperial.ac.uk]"
            )


class TimeEntry(models.Model):
    """Time entry for a user."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text="The team member this time entry relates to.",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        help_text="The project this time entry relates to.",
    )

    start_time = models.DateTimeField(
        "Start time",
        null=False,
        blank=False,
        help_text="The date and time when the work started.",
    )
    end_time = models.DateTimeField(
        "End time",
        null=False,
        blank=False,
        help_text="The date and time when the work ended.",
    )
    monthly_charge = models.ManyToManyField(
        MonthlyCharge,
        blank=True,
        help_text="The relevant monthly charge for this time entry.",
    )

    clockify_id = models.CharField(
        "Clockify ID",
        blank=True,
        null=False,
        help_text="The ID of the time entry in Clockify, if applicable.",
    )

    def __str__(self) -> str:
        """String representation of the Time Entry object."""
        return f"{self.user} - {self.project} - {self.start_time} to {self.end_time}"


class FullTimeEquivalent(models.Model):
    """Full-time-equivalent model for user and projects."""

    class Meta:
        """Model metadata."""

        abstract = True

    value = models.FloatField(
        "FTE value",
        blank=False,
        null=False,
        help_text="The full-time-equivalent value over the specified period.",
    )

    start_date = models.DateField(
        "Start date",
        null=False,
        blank=False,
        help_text="The date when the FTE begins.",
    )

    end_date = models.DateField(
        "End date",
        null=False,
        blank=False,
        help_text="The date when the FTE ends.",
    )

    @classmethod
    def from_days(  # type: ignore[explicit-any]
        cls,
        days: int,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> None:
        """Creates an FTE object given a number of days time period."""
        # get date difference in fractional days
        date_difference = (end_date - start_date).days
        # use WORKING_DAYS to estimate day_difference minus weekends & holidays
        day_difference = date_difference * WORKING_DAYS / 365
        # FTE will then be the # of days work / the (weighted) time period in days
        cls.objects.create(  # type: ignore[attr-defined]
            value=days / day_difference,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

    @property
    def days(self) -> int:
        """Convert FTE to days using the working days in a year in the settings."""
        date_difference = (self.end_date - self.start_date).days

        return round(self.value * date_difference * WORKING_DAYS / 365)

    def trace(self, timerange: pd.DatetimeIndex | None = None) -> "pd.Series[float]":
        """Convert the FTE to a dataframe.

        If timerange is provided, those dates are used, otherwise a datetime index is
        created using the start and end dates of the FTE object.
        """
        if timerange:
            idx = timerange.copy()
        else:
            idx = pd.date_range(start=self.start_date, end=self.end_date)

        return pd.Series(self.value, index=idx)

    def clean(self) -> None:
        """Ensure start date comes before end date and that value 0 or positive."""
        super().clean()
        if self.end_date <= self.start_date:
            raise ValidationError("The end date must be after the start date.")

        if self.value < 0:
            raise ValidationError(
                "The FTE value must be greater than or equal to zero."
            )
