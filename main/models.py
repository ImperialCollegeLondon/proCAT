"""Models module for main app."""

from django.contrib.auth.models import AbstractUser
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
