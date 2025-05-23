"""Models module for main app."""

from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
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
    def days_left(self) -> tuple[int, float] | None:
        """Provide the days worth of effort left.

        TODO: Placeholder. To be implemented when funding is implemented.

        Returns:
            The number of days worth of effort left, or None if there is no funding
            information.
        """
        return 42, 48.0
