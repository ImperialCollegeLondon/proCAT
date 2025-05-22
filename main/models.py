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
