"""Models module for main app."""

from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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


class ActivityCode(models.Model):
    """Activity code to use during charging."""

    code = models.IntegerField(
        "Code",
        unique=True,
        blank=False,
        null=False,
        help_text="Code for the activity to use during charging.",
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
        """String representation of the Activity Code object."""
        return f"{self.code} - {self.description}"


class Project(models.Model):
    """Software project details."""

    _NATURE = (("Support", "Support"), ("Standard", "Standard"))
    _STATUS = (
        ("Draft", "Draft"),
        ("Not started", "Not started"),
        ("Active", "Active"),
        ("Completted", "Completted"),
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
        default="Draft",
        choices=_STATUS,
        help_text="Status of the project. Unless the status is 'Draft', most other "
        "fields are mandatory.",
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

    def __str__(self) -> str:
        """String representation of the Project object."""
        return self.name

    def clean(self) -> None:
        """Ensure that all fields have a value unless the status is 'Draft'.

        It also checks that, if present, the end date is after the start date.
        """
        if self.status == "Draft":
            return super().clean()

        if not self.start_date or not self.end_date or not self.lead:
            raise ValidationError(
                "All fields are mandatory except if Project status id 'Draft'."
            )

        if self.end_date <= self.start_date:
            raise ValidationError("The end date must be after the start date.")

    @property
    def weeks_to_deadline(self) -> tuple[int, float] | None:
        """Provide the number of weeks left until project deadline.

        Only relevant for active projects.

        Returns:
            The number of weeks left or None if the project is not Active.
        """
        if self.status == "Active" and self.end_date and self.start_date:
            left = (self.end_date - datetime.now().date()).days / 7
            total = (self.end_date - self.start_date).days / 7
            return int(left), round(left / total * 100, 1)

        return None

    @property
    def total_effort(self) -> int | None:
        """Provide the total days worth of effort available from funding.

        Returns:
            The total number of days effort, or None if there is no funding information.
        """
        if self.funding_source.exists():
            total = sum([funding.effort for funding in self.funding_source.all()])
            return total

        return None

    @property
    def days_left(self) -> tuple[int, float] | None:
        """Provide the days worth of effort left.

        Returns:
            The number of days and percentage worth of effort left, or None if there is
            no funding information.
        """
        if self.funding_source.exists() and self.total_effort:
            left = sum([funding.effort_left for funding in self.funding_source.all()])
            return left, round(left / self.total_effort * 100, 1)

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

    project_code = models.CharField(
        "Project code",
        blank=True,
        null=True,
        help_text="The funding code designated to the project.",
    )

    activity_code = models.ForeignKey(
        ActivityCode,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="The activity code to use for charging.",
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
        help_text="The total budget for the funding.",
    )

    daily_rate = models.DecimalField(
        "Daily rate",
        default=389.00,
        blank=False,
        null=False,
        max_digits=12,
        decimal_places=2,
        help_text="The current daily rate, which defaults to 389.00.",
    )

    class Meta:
        """Meta class for the model."""

        verbose_name_plural = "funding"

    def __str__(self) -> str:
        """String representation of the Funding object."""
        return f"{self.project} - £{self.budget:.2f} - {self.project_code}"

    def clean(self) -> None:
        """Ensure that all fields have a value unless the source is 'Internal'."""
        if self.source == "Internal":
            return super().clean()

        if (
            not self.funding_body
            or not self.project_code
            or not self.activity_code
            or not self.expiry_date
        ):
            raise ValidationError(
                "All fields are mandatory except if source is 'Internal'."
            )

    @property
    def effort(self) -> int:
        """Provide the effort in days, calculated based on the budget and daily rate.

        Returns:
            The total number of days of effort provided by the funding.
        """
        days_effort = round(self.budget / self.daily_rate)
        return days_effort

    @property
    def effort_left(self) -> int:
        """Provide the effort left in days.

        TODO: Placeholder. To be implemented when synced with Clockify.

        Returns:
            The number of days worth of effort left.
        """
        return 42


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
