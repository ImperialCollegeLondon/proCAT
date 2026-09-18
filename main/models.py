"""Models module for main app."""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import UTC, date, timedelta
from typing import Any, cast

import pandas as pd
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from procat.settings.settings import (
    EFFORT_LEFT_THRESHOLD,
    WEEKS_LEFT_THRESHOLD,
    WORKING_DAYS,
)

from .models_utils import Warning


class User(AbstractUser):
    """Custom user model."""

    def __str__(self) -> str:
        """Full name of the user."""
        return f"{self.first_name} {self.last_name}"


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


class Project(Warning, models.Model):
    """Software project details."""

    _NATURE = (("Support", "Support"), ("Standard", "Standard"))
    _STATUS = (
        ("Tentative", "Tentative"),
        ("Confirmed", "Confirmed"),
        ("Active", "Active"),
        ("Finished", "Finished"),
        ("Not done", "Not done"),
        ("Maintenance", "Maintenance"),
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

    def _warn_no_funding(self) -> None | str:
        """Warns if there is no funding associated to the project."""
        if not self.funding_source.exists() or not all(
            [f.is_complete() for f in self.funding_source.all()]
        ):
            return "No funding defined for the project or incomplete row."
        return None

    def _warn_phase_lifetime(self) -> None | str:
        """Warns if the phases don't cover the project lifetime."""
        # Projects without a start date (e.g. still 'Tentative') haven't
        # started yet, so there is no lifetime for phases to span.
        if self.start_date is None:
            return None

        # get phases for project id
        phases_query = ProjectPhase.objects.filter(project__name=self.name)

        # check start overlaps
        starts = phases_query.filter(start_date=self.start_date).exists()

        # iterate through phase end dates checking alignment with starts or project end.
        span = False
        for query in phases_query:
            expected_start_date = query.end_date + timedelta(days=1)
            span = (
                phases_query.filter(start_date=expected_start_date).exists()
                or self.end_date == query.end_date
            )
            if not span:
                break

        # do the check
        if not (starts or span):
            return "Phases do not span project lifetime."
        return None

    def _warn_wrong_days_sum(self) -> str | None:
        """Warns if the phases do not sum to the total working days for the project."""
        if not self.funding_source.exists():
            return None

        project_days = sum([f.effort for f in self.funding_source.all()])

        if not project_days:
            return None

        # get query for project name
        phase_days = sum(
            phase.days for phase in ProjectPhase.objects.filter(project__name=self.name)
        )

        # do the check
        if not math.isclose(project_days, phase_days, abs_tol=1e-2):
            return (
                f"Project days ({project_days:.1f}) do not match "
                f"Phase days ({phase_days:.1f})."
            )
        return None

    def clean(self) -> None:
        """Ensure all fields have a value unless status is 'Tentative' or 'Not done'.

        It also checks that, if present, the end date is after the start date.
        In addition, a project that was not yet 'Active' or 'Maintenance', but wants to,
        cannot have warnings; the project must start clean
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

        # No more checks if the project status is not set to become
        # 'Active', 'Confirmed', or 'Maintenance'
        if self.status not in ("Active", "Confirmed", "Maintenance"):
            return

        if self.pk is None:
            raise ValidationError(
                "Projects cannot be created directly in Active, Confirmed, or "
                "Maintenance statuses."
            )
        else:
            was_active = Project.objects.filter(
                pk=self.pk, status__in=("Active", "Confirmed", "Maintenance")
            ).exists()
            if not was_active and self.has_warnings:
                message = (
                    "A project cannot be made Active, Confirmed, or Maintenance if "
                    "there are warnings:"
                )
                raise ValidationError([message, *self.warnings])

        # Check that a project has two phases and one maintenance phase if it is set
        # to Maintenance status.
        if self.status == "Maintenance" and (
            not self.phases.filter(is_maintenance=True).exists()
            or self.phases.count() < 2
        ):
            raise ValidationError(
                "Projects cannot be set to Maintenance status unless there "
                "is exactly one maintenance phase and at least 2 phases."
            )

    @property
    def weeks_to_deadline(self) -> tuple[float, float] | None:
        """Provide the number of weeks left until project deadline.

        Only relevant for projects in Active, Confirmed, and Maintenance statuses.

        Returns:
            The number of weeks left or None if the project is Tentative or Not done.
        """
        if (
            self.status in ["Active", "Confirmed", "Maintenance"]
            and self.end_date
            and self.start_date
        ):
            left = (self.end_date - timezone.now().date()).days / 7
            total = (self.end_date - self.start_date).days / 7
            return left, left / total * 100

        return None

    @property
    def total_effort(self) -> float | None:
        """Provide the total days worth of effort available.

        For projects in Maintenance status, the total effort is the one associated to
        the maintenance phase. For projects in Active status, the total effort is the
        sum of the days associated to all non-maintenance phases (this deliberately
        excludes a maintenance phase that may already have been set up in
        preparation for a future transition to Maintenance status). If an Active
        project has no phases defined yet, funding is used instead: this preserves the
        prior behaviour for projects that don't use the phases feature, and avoids a
        circular dependency when creating the very first phase for a project (since
        `total_effort` may be used to seed the initial phase created for a project).
        For all other statuses, the total effort is derived from the funding sources,
        as before.

        Returns:
            The total number of days effort, or None if there is no relevant
            information (funding or phases, depending on status) to derive it from.
        """
        if self.status == "Maintenance":
            maint = self.maintenance_phase()
            return maint.days if maint is not None else None

        if self.status == "Active":
            non_maintenance_phases = self.phases.filter(is_maintenance=False)
            if non_maintenance_phases.exists():
                return sum(phase.days for phase in non_maintenance_phases)

        if self.funding_source.exists():
            total = sum([funding.effort for funding in self.funding_source.all()])
            return total

        return None

    @property
    def total_funding_left(self) -> float | None:
        """Provide the total funding left after deducting confirmed charges.

        In maintenance mode or if the project is finished, this is not relevant, despite
        having a funding source. For all other statuses, if there's funding information,
        it should be calculated out of it.

        Returns:
            The total monetary amount of funding left, or none if there is no funding
            information.
        """
        if self.status in ("Maintenance", "Finished"):
            return None

        if self.funding_source.exists():
            total = sum(
                [funding.funding_left for funding in self.funding_source.all()],
                0,
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

        if not self.total_effort:
            return None

        if self.status != "Maintenance":
            time_entries = self.timeentry_set.all()

            # If an Active project already has a phase flagged for a future
            # transition to Maintenance, only entries logged before that phase
            # starts should count towards the (non-maintenance) total_effort.
            if self.status == "Active" and (maint_phase := self.maintenance_phase()):
                time_entries = time_entries.filter(
                    start_time__lt=maint_phase.start_date
                )

            hours_logged = get_logged_hours(time_entries)[0]
            left = self.total_effort - (hours_logged / 7)
            return left, left / self.total_effort * 100

        maint_phase = self.maintenance_phase()
        if maint_phase is None:
            return None
        time_entries = self.timeentry_set.filter(start_time__gte=maint_phase.start_date)
        hours_logged = get_logged_hours(time_entries)[0]
        pro_rata_used_maint = maint_phase.days - maint_phase.expected_days_left
        left = maint_phase.days - max(pro_rata_used_maint, (hours_logged / 7))
        return left, left / maint_phase.days * 100

    def maintenance_phase(self) -> ProjectPhase | None:
        """Provide the phase flagged as the maintenance phase of the project, if any.

        This is not restricted to projects currently in Maintenance status: an Active
        project may already have a phase flagged in preparation for a future
        transition to Maintenance.

        Returns:
            The maintenance phase, or None if there is no maintenance phase.
        """
        return self.phases.filter(is_maintenance=True).first()

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
    def total_working_days(self) -> float | None:
        """Provide the total number of working days given the funding.

        Returns:
            Number of working days given the funding available.
        """
        if self.start_date and self.end_date:
            # `start_date`/`end_date` are an inclusive calendar range (both days
            # count towards the project), hence the `+ 1`.
            days = (self.end_date - self.start_date).days + 1
            return (days / 365) * WORKING_DAYS
        return None

    def fte(self, timerange: pd.DatetimeIndex | None = None) -> pd.Series:  # type: ignore[explicit-any]
        """Calculate the FTE trace for the project over a given timerange.

        This is calculated by summing the trace of all the phases of the project,
        which are assumed to be sequential and non-overlapping.

        Args:
            timerange: The timerange to calculate the FTE trace over.

        Returns:
            A pandas Series with the FTE trace over the timerange, or a trace of 0 if
            there are no phases.
        """
        assert self.start_date is not None
        assert self.end_date is not None

        timerange = (
            timerange
            if timerange is not None
            else pd.date_range(start=self.start_date, end=self.end_date, tz=UTC)
        )
        if self.phases.exists():
            return cast(  # type: ignore[explicit-any]
                pd.Series, sum(phase.trace(timerange) for phase in self.phases.all())
            ) + self._excess_fte(timerange)
        return pd.Series(0.0, index=timerange)

    def _excess_fte(self, timerange: pd.DatetimeIndex) -> pd.Series:  # type: ignore[explicit-any]
        """Calculate the excess FTE due to not using enough time of a project.

        This will be homogeneously spread over the remaining time of the project. If
        time left is more than what it should, then the excess FTE will be positive,
        otherwise, it will be zero.

        Args:
            timerange: The timerange to calculate the excess FTE trace over.

        Returns:
            A pandas Series with the excess FTE trace over the timerange.
        """
        assert self.end_date is not None

        from .utils import days_to_fte

        output = pd.Series(0.0, index=timerange)
        if not self.phases.exists() or not self.days_left:
            return output

        # Extra days available
        expected_left = sum(phase.expected_days_left for phase in self.phases.all())
        excess_left = max(self.days_left[0] - expected_left, 0)

        # Period to use them
        now = timezone.now()

        # Actual excess full time equivalent needed to use those days over the time left
        excess_fte = days_to_fte(now.date(), self.end_date, excess_left)
        output.loc[now : pd.Timestamp(self.end_date, tz=UTC)] = excess_fte

        return output


class DailyRate(models.Model):
    """Historical record of the standard daily rate used for funding.

    Rather than storing a single mutable value, each change to the standard
    rate is recorded as a new entry, effective from a given date. This keeps
    an audit trail of how the standard rate has changed over time, and lets a
    new rate be scheduled ahead of its effective date if needed.

    This only supplies the *default* value proposed when a new `Funding`
    record is created (see `get_current_daily_rate`). Each `Funding.daily_rate`
    remains independently editable, so funding sources that use a bespoke rate
    (different from the standard one at that point in time) can simply have
    their rate set accordingly, and it won't be affected by later additions
    here.
    """

    rate = models.DecimalField(
        "Daily rate",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="The standard daily rate, effective from 'Effective date'.",
    )

    effective_date = models.DateField(
        "Effective date",
        default=timezone.now,
        help_text="The date from which this daily rate applies.",
    )

    class Meta:
        """Meta class for the model."""

        ordering = ("-effective_date",)
        verbose_name_plural = "daily rates"

    def __str__(self) -> str:
        """String representation of the DailyRate object."""
        return f"£{self.rate:.2f} (from {self.effective_date})"


# Used as a last resort by `get_current_daily_rate` if no `DailyRate` has been
# created yet, e.g. on a fresh database before the initial one is seeded.
FALLBACK_DAILY_RATE = 450.00


def get_current_daily_rate() -> float:
    """Provide the currently applicable standard daily rate.

    Used as the default value for new `Funding` records. Existing records are
    unaffected by later changes to the standard rate, since `daily_rate` is
    stored on each `Funding` individually rather than looked up live.

    Returns:
        The rate of the most recent `DailyRate` whose `effective_date` is not
        in the future, or `FALLBACK_DAILY_RATE` if none exists yet.
    """
    current = (
        DailyRate.objects.filter(effective_date__lte=timezone.now().date())
        .order_by("-effective_date", "-pk")
        .first()
    )
    return float(current.rate) if current is not None else FALLBACK_DAILY_RATE


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
        default=get_current_daily_rate,
        blank=False,
        null=False,
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="The daily rate for this funding. Defaults to the current "
        "standard rate (see the 'Daily rates' admin section), but can be "
        "overridden for funding sources that use a different, bespoke rate.",
    )

    class Meta:
        """Meta class for the model."""

        verbose_name_plural = "funding"

    def __str__(self) -> str:
        """String representation of the Funding object."""
        return f"{self.project} - £{self.budget:.2f} - {self.project_code}"

    def clean(self) -> None:
        """Ensure that the activity code has a valid value."""
        try:
            project = self.project
        except ObjectDoesNotExist:
            project = None

        if (
            project
            and project.status in ("Active", "Confirmed", "Maintenance")
            and not self.is_complete()
        ):
            raise ValidationError(
                "Funding of Active, Confirmed, and Maintenance projects must "
                "be complete."
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
        return float(self.budget / self.daily_rate)

    @property
    def funding_left(self) -> float:
        """Provide the funding left in currency.

        Funding left is calculated based on 'Confirmed' monthly charges.

        Returns:
            The amount of funding left.
        """
        funding_spent = MonthlyCharge.objects.filter(
            funding=self, status="Confirmed"
        ).aggregate(Sum("amount"))["amount__sum"]
        if funding_spent:
            return float(self.budget - funding_spent)
        return float(self.budget)

    @property
    def effort_left(self) -> float:
        """Provide the effort left in days.

        Returns:
            The number of days worth of effort left.
        """
        return self.funding_left / float(self.daily_rate)

    def monthly_pro_rata_charge(self, date: date) -> float | None:
        """Calculate the charge per month if the project has Pro-rata charging.

        Calculates the number of months between project start and end date regardless
        of the day of the month so the monthly charge will be the same regardless
        of the number of days in the month.

        The last month of the project is not charged, so the charge applies from the
        month of the start date until the month before the end date, to ensure that no
        charges are made outside of the project period. For example, if a project
        starts on 15th January and ends on 10th April, the charge will apply for
        January, February and March, but not April.

        Args:
            date: The date for which to calculate the monthly charge, used to check if
                the project has started and hasn't ended yet.

        Returns:
            The monthly charge amount, or None if the project doesn't have Pro-rata
            charging or the date is outside the project period.
        """
        if (
            self.project.charging == "Pro-rata"
            and self.project.start_date
            and self.project.end_date
            and self.project.start_date.month
            <= date.month
            < self.project.end_date.month
        ):
            months = (
                self.project.end_date.year - self.project.start_date.year
            ) * 12 + (self.project.end_date.month - self.project.start_date.month)
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
        days: float,
        start_date: date,
        end_date: date,
        **kwargs: Any,
    ) -> None:
        """Creates an FTE object given a number of days time period."""
        from .utils import days_to_fte

        # FTE will then be the # of days work / the (weighted) time period in days.
        # `start_date`/`end_date` are an inclusive calendar range (both days count
        # towards the period), hence the `+ timedelta(days=1)`.
        obj = cls(
            value=days_to_fte(start_date, end_date + timedelta(days=1), days),
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )
        obj.clean()
        obj.save()

    @property
    def days(self) -> float:
        """Convert FTE to days using the working days in a year in the settings."""
        from .utils import fte_to_days

        # `start_date`/`end_date` are an inclusive calendar range (both days count
        # towards the period), hence the `+ timedelta(days=1)`.
        return fte_to_days(
            self.start_date, self.end_date + timedelta(days=1), self.value
        )

    def trace(self, timerange: pd.DatetimeIndex | None = None) -> pd.Series[float]:
        """Convert the FTE to a dataframe.

        If timerange is provided, those dates are used, otherwise a datetime index is
        created using the start and end dates of the FTE object.
        """
        if timerange is not None:
            idx = timerange.copy()
            output = pd.Series(0.0, index=idx)
            output.loc[
                pd.Timestamp(self.start_date, tz=UTC) : pd.Timestamp(
                    self.end_date, tz=UTC
                )
            ] = self.value
        else:
            idx = pd.date_range(start=self.start_date, end=self.end_date, tz=UTC)
            output = pd.Series(self.value, index=idx)

        return output

    def clean(self) -> None:
        """Ensure start date comes before end date and that value 0 or positive."""
        super().clean()
        if self.end_date <= self.start_date:
            raise ValidationError("The end date must be after the start date.")

        if self.value < 0:
            raise ValidationError(
                "The FTE value must be greater than or equal to zero."
            )


class ProjectPhase(FullTimeEquivalent):
    """Phases associated with a project."""

    project = models.ForeignKey(
        Project,
        related_name="phases",
        on_delete=models.CASCADE,
    )

    is_maintenance = models.BooleanField(
        "Is maintenance phase",
        default=False,
        help_text="Indicates if this phase is the maintenance phase of the project.",
    )

    def __str__(self) -> str:
        """String representation of the ProjectPhase object."""
        return f"{self.project.name} - {self.start_date} -> {self.end_date}"

    def save(self, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        """Saves the object to the database.

        This overwrites models.Model.save() to keep the days constant if the start or
        end date changes, modifying the FTE value. Except if `value` has also changed in
        the same modification.
        """
        from .utils import days_to_fte

        update_fields = kwargs.get("update_fields", {})

        # If value has changed, then we don't do anything extra
        if "value" in update_fields:
            pass

        # If dates change, we update the value so the days remain constant
        elif "start_date" in update_fields or "end_date" in update_fields:
            # get old date (from DB)
            old_days = ProjectPhase.objects.get(pk=self.pk).days
            # update the value keeping the days constant by updating FTE value
            # `end_date` is inclusive, hence the `+ timedelta(days=1)`.
            self.value = days_to_fte(
                self.start_date, self.end_date + timedelta(days=1), old_days
            )
            kwargs["update_fields"] = {"value"}.union(update_fields)

        super().save(**kwargs)

    def check_phase_in_project(self) -> None:
        """Ensure the start phase dates are within the project dates."""
        if self.project.start_date is None or self.project.end_date is None:
            raise ValidationError(
                "Phases cannot be added until the project has a start and end date."
            )
        if (
            self.project.start_date > self.start_date
            or self.project.end_date < self.end_date
        ):
            raise ValidationError(
                "Phase period must be within the project period: "
                f"{self.project.start_date} -> {self.project.end_date}"
            )

    def check_overlapping_phases(
        self, siblings: Iterable[ProjectPhase] | None = None
    ) -> None:
        """Check the phase doesn't overlap with another phase (by 1 day).

        Args:
            siblings: The other phases of the same project to check against. If
                not given (the default), the project's other phases are fetched
                from the database, which is the correct behaviour when
                validating a single phase on its own (e.g. from the admin, the
                API, or a direct `save()`/`full_clean()` call). An explicit list
                can be passed instead to validate against phases that have not
                been persisted yet, e.g. when several phases belonging to the
                same project are being created or edited together (see
                `ProjectPhaseInlineFormSet`, in `forms.py`).
        """
        if siblings is None:
            siblings = ProjectPhase.objects.filter(project=self.project)
            if self.pk:
                siblings = siblings.exclude(pk=self.pk)

        # check start within Phases_starts ≤ Phase_new_start ≤ Phases_ends, or
        # end within Phases_starts ≤ Phase_new_end ≤ Phases_ends
        conflict = next(
            (
                sibling
                for sibling in siblings
                if sibling is not self
                and (
                    sibling.start_date <= self.start_date <= sibling.end_date
                    or sibling.start_date <= self.end_date <= sibling.end_date
                )
            ),
            None,
        )

        if conflict is not None:
            raise ValidationError(
                "Phase period must not overlap with other phase periods for the same "
                f"project: {conflict.start_date} -> "
                f"{conflict.end_date} vs. {self.start_date} -> {self.end_date}"
            )

    def check_phase_alignment(
        self, siblings: Iterable[ProjectPhase] | None = None
    ) -> None:
        """Ensures phases are aligned but separated by 1 day.

        Args:
            siblings: See `check_overlapping_phases`.
        """
        if siblings is None:
            siblings = ProjectPhase.objects.filter(project=self.project)

        touching = any(
            sibling.start_date == self.end_date + timedelta(days=1)
            or sibling.end_date == self.start_date - timedelta(days=1)
            for sibling in siblings
        )

        if not (
            touching
            or self.start_date == self.project.start_date
            or self.end_date == self.project.end_date
        ):
            raise ValidationError(
                "Phase period must align with the start or end of a project or phase."
            )

    def check_only_one_maintenance_phase(
        self, siblings: Iterable[ProjectPhase] | None = None
    ) -> None:
        """Ensure only one maintenance phase exists for the project.

        Args:
            siblings: See `check_overlapping_phases`.
        """
        if not self.is_maintenance:
            return

        if siblings is None:
            existing_maintenance = ProjectPhase.objects.filter(
                project=self.project, is_maintenance=True
            )
            if self.pk:
                existing_maintenance = existing_maintenance.exclude(pk=self.pk)
            has_other_maintenance = existing_maintenance.exists()
        else:
            has_other_maintenance = any(
                sibling.is_maintenance for sibling in siblings if sibling is not self
            )

        if has_other_maintenance:
            raise ValidationError("Only one maintenance phase is allowed per project.")

    def clean(self) -> None:
        """Ensures that phase dates are sensible.

        Ensures start is before the end date (from FTE clean).
        Ensures phase within project period.
        Ensures the phase isn't covered by any other phases.
        Ensures at least phase start or end date aligns with other phases or project
            dates.

        The sibling-dependent checks (overlap, alignment, single maintenance
        phase) are skipped here if `_validated_by_formset` has been set on this
        instance: in that case, `ProjectPhaseInlineFormSet.clean()` (see
        `forms.py`) performs them itself, once, against the complete in-memory
        set of phases being submitted together, rather than one at a time
        against the database.
        """
        super().clean()

        try:
            self.project
        except ObjectDoesNotExist:
            # Nothing else can be checked without a project to check against.
            # Django's own required-field validation will already flag the
            # missing `project` field separately (e.g. when this is used as a
            # standalone form, or when the inline Project/Phase form
            # redisplays phase rows after the Project itself failed
            # validation, before either has been saved).
            return

        self.check_phase_in_project()

        if getattr(self, "_validated_by_formset", False):
            return

        self.check_overlapping_phases()
        self.check_phase_alignment()
        self.check_only_one_maintenance_phase()

    @property
    def expected_days_left(self) -> float:
        """Expected number of days left in the phase.

        If the days were to be used homogeneously over the phase length, this function
        calculates how many days of effort are left from today. In phases that have not
        started (today < start date), the days left will be the total number of days,
        and phases that are gone (today > end date) the total number of days will be
        zero.
        """
        total_calendar_days = (self.end_date - self.start_date).days
        fraction_left = min(
            1,
            max((self.end_date - timezone.now().date()).days, 0) / total_calendar_days,
        )
        return fraction_left * self.days
