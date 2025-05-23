"""Tests for the models."""

from datetime import datetime, timedelta

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
        from django.core.exceptions import ValidationError

        from main import models

        # Mandatory fields are present
        project = models.Project(name="ProCAT", status="Active")
        with pytest.raises(
            ValidationError,
            match="All fields are mandatory except if Project status id 'Draft'.",
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

    @pytest.mark.parametrize(
        ["status", "start_date", "end_date", "output"],
        [
            ["Draft", None, None, None],
            ["Active", datetime.now().date(), None, None],
            ["Active", None, datetime.now().date(), None],
            ["Draft", datetime.now().date(), datetime.now().date(), None],
            [
                "Active",
                datetime.now().date(),
                datetime.now().date() + timedelta(days=1),
                (0, 100.0),
            ],
        ],
    )
    def test_weeks_to_deadline(self, status, start_date, end_date, output):
        """Test the weeks_to_deadline method."""
        from main import models

        project = models.Project(
            name="ProCAT", status=status, start_date=start_date, end_date=end_date
        )
        assert project.weeks_to_deadline == output


class TestFunding:
    """Tests for the funding model."""

    def test_model_str(self):
        """Test the object string for the funding model."""
        from main import models

        funding = models.Funding(funding_body="EPSRC", project_code="1234")
        assert str(funding) == "EPSRC - 1234"

    def test_effort(self):
        """Test effort calculated from budget and daily rate."""
        from main import models

        funding = models.Funding(budget=10000.00, daily_rate=389.00)
        assert funding.effort == 25

    def test_clean_when_internal(self):
        """Test the clean method."""
        from main import models

        funding = models.Funding(source="Internal")
        funding.clean()

    def test_clean_when_external(self):
        """Test the clean method."""
        from django.core.exceptions import ValidationError

        from main import models

        # test with missing fields
        funding = models.Funding(source="External")
        with pytest.raises(
            ValidationError,
            match="All fields are mandatory except if source is 'Internal'.",
        ):
            funding.clean()

        # all fields present
        activity_code = models.ActivityCode(
            code="1234", description="Some code", notes="None"
        )

        funding = models.Funding(
            source="External",
            funding_body="EPSRC",
            project_code="1234",
            activity_code=activity_code,
            expiry_date=datetime.now().date(),
        )
        funding.clean()
