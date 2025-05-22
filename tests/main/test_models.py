"""Tests for the models."""

import pytest


def test_department_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.Department(name="ICT", faculty="Other")
    assert str(dep) == "ICT - Other"


def test_activity_code_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.ActivityCode(code="1234", description="Some code", notes="None")
    assert str(dep) == "1234 - Some code"


class TestProject:
    """Tests for the project model."""

    def test_model_str(self):
        """Test the object string for the model."""
        from main import models

        project = models.Project(name="ProCAT")
        assert str(project) == "ProCAT"

    def test_clean_when_draft(self):
        """Test the clean method."""
        from main import models

        project = models.Project(name="ProCAT")
        project.clean()

    def test_clean_when_not_draft(self, user):
        """Test the clean method."""
        from datetime import datetime, timedelta

        from django.core.exceptions import ValidationError

        from main import models

        # Mandatory fields are present
        project = models.Project(name="ProCAT", status="Active")
        with pytest.raises(
            ValidationError,
            match="All fields are mandatory except if Project status is 'Draft'.",
        ):
            project.clean()

        # The end date is after the start date
        project = models.Project(
            name="ProCAT",
            lead=user,
            start_date=datetime.now().date(),
            end_date=datetime.now().date(),
            status="Active",
        )
        with pytest.raises(
            ValidationError,
            match="The end date must be after the start date.",
        ):
            project.clean()

        # All good!
        project = models.Project(
            name="ProCAT",
            lead=user,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=42),
            status="Active",
        )
        project.clean()
