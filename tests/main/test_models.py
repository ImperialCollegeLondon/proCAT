"""Tests for the models."""

from contextlib import nullcontext as does_not_raise
from datetime import datetime, timedelta

import pytest
from django.core.exceptions import ValidationError


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

    @pytest.mark.django_db
    @pytest.mark.usefixtures("department", "user", "activity_code")
    def test_total_effort(self):
        """Test the total_effort method."""
        from main import models

        department = models.Department.objects.get(name="ICT")
        user = models.User.objects.get(username="testuser")
        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
        )
        assert project.total_effort is None

        activity_code = models.ActivityCode.objects.get(code="1234")
        funding_A = models.Funding.objects.create(
            project=project,
            source="External",
            project_code="1234",
            activity_code=activity_code,
            budget=10000.00,
        )
        funding_B = models.Funding.objects.create(
            project=project,
            source="External",
            project_code="5678",
            activity_code=activity_code,
            budget=5000.00,
        )
        total_effort = funding_A.effort + funding_B.effort
        assert project.total_effort == total_effort

    @pytest.mark.django_db
    @pytest.mark.usefixtures("department", "user", "activity_code")
    def test_days_left(self):
        """Test the days_left method."""
        from main import models

        department = models.Department.objects.get(name="ICT")
        user = models.User.objects.get(username="testuser")
        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
        )
        assert project.days_left is None

        activity_code = models.ActivityCode.objects.get(code="1234")
        funding_A = models.Funding.objects.create(
            project=project,
            source="External",
            project_code="1234",
            activity_code=activity_code,
            budget=10000.00,
        )
        funding_B = models.Funding.objects.create(
            project=project,
            source="External",
            project_code="5678",
            activity_code=activity_code,
            budget=5000.00,
        )
        total_effort = funding_A.effort + funding_B.effort
        left = funding_A.effort_left + funding_B.effort_left
        days_left = left, round(left / total_effort * 100, 1)
        assert project.days_left == days_left


class TestFunding:
    """Tests for the funding model."""

    def test_model_str(self):
        """Test the object string for the funding model."""
        from main import models

        project = models.Project(name="ProCAT")
        funding = models.Funding(project=project, budget=10000.00, project_code="1234")
        assert str(funding) == "ProCAT - £10000.00 - 1234"

    def test_effort(self):
        """Test effort calculated from budget and daily rate."""
        from main import models

        funding = models.Funding(budget=10000.00, daily_rate=389.00)
        assert funding.effort == 26

    def test_clean_when_internal(self):
        """Test the clean method."""
        from main import models

        funding = models.Funding(source="Internal")
        funding.clean()

    def test_clean_when_external(self):
        """Test the clean method."""
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

    @pytest.mark.parametrize(
        ["budget", "expectation"],
        [
            [-1000.00, pytest.raises(ValidationError)],
            [0.00, does_not_raise()],
            [1000.00, does_not_raise()],
        ],
    )
    def test_budget(self, project, activity_code, budget, expectation):
        """Test that the budget cannot be a negative value."""
        from main import models

        funding = models.Funding.objects.create(
            project=project,
            source="External",
            funding_body="EPSRC",
            project_code="1234",
            activity_code=activity_code,
            expiry_date=datetime.now().date(),
            budget=budget,
            daily_rate=389.00,
        )
        with expectation:
            funding.full_clean()

    @pytest.mark.parametrize(
        ["daily_rate", "expectation"],
        [
            [-389.00, pytest.raises(ValidationError)],
            [0.00, does_not_raise()],
            [389.00, does_not_raise()],
        ],
    )
    def test_daily_rate(self, project, activity_code, daily_rate, expectation):
        """Test that the daily rate cannot be a negative value."""
        from main import models

        funding = models.Funding(
            project=project,
            source="External",
            funding_body="EPSRC",
            project_code="1234",
            activity_code=activity_code,
            expiry_date=datetime.now().date(),
            budget=1000.00,
            daily_rate=daily_rate,
        )
        with expectation:
            funding.full_clean()


class TestCapacity:
    """Tests for the capacity model."""

    def test_model_str(self, user):
        """Test the object string for the capacity model."""
        from main import models

        capacity = models.Capacity(
            user=user, value=0.5, start_date=datetime.now().date()
        )
        assert (
            str(capacity)
            == f"From {datetime.now().date()}, the capacity of {user!s} is 0.5."
        )

    @pytest.mark.parametrize(
        ["value", "is_valid"],
        [
            [-0.5, False],
            [0.0, True],
            [0.5, True],
            [1.0, True],
            [1.5, False],
        ],
    )
    def test_value(self, user, value, is_valid):
        """Test that the value of capacity can only between 0 and 1."""
        from main import models

        capacity = models.Capacity(
            user=user, value=value, start_date=datetime.now().date()
        )
        if is_valid:
            # Should not raise
            capacity.full_clean()
        else:
            with pytest.raises(ValidationError):
                capacity.full_clean()


class TestTimeEntry:
    """Tests for the time entry model."""

    def test_model_str(self, user, project):
        """Test the object string for the time entry model."""
        from main import models

        time_entry = models.TimeEntry(
            user=user,
            project=project,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=7.5),
        )
        assert (
            str(time_entry)
            == f"{user!s} - {project!s} - {time_entry.start_time} to {time_entry.end_time}"  # noqa: E501
        )
