
"""Tests for the models."""

from contextlib import nullcontext as does_not_raise
from datetime import date, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError


def test_department_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.Department(name="ICT", faculty="Other")
    assert str(dep) == "ICT - Other"


def test_analysis_code_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.AnalysisCode(code="1234", description="Some code", notes="None")
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
        project = models.Project(name="ProCAT", status="Not Started")
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
            status="Not Started",
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
            status="Not Started",
        )
        project.clean()

    def test_clean_when_project_active(self, user, department):
        """Test the clean method."""
        from main import models

        # All good!
        project = models.Project(
            name="ProCAT",
            lead=user,
            department=department,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=42),
            status="Not Started",
        )
        project.clean()
        project.save()

        # No funding, no active
        project.status = "Active"
        with pytest.raises(
            ValidationError,
            match="Active projects must have at least 1 funding source.",
        ):
            project.clean()

        # Add funding source and all works!
        models.Funding.objects.get_or_create(
            project=project,
            source="Internal",
            budget=10000.00,
        )
        project.clean()

    @pytest.mark.parametrize(
        ["status", "start_date", "end_date", "output"],
        [
            ["Draft", None, None, None],
            ["Not Started", datetime.now().date(), None, None],
            ["Not Started", None, datetime.now().date(), None],
            ["Draft", datetime.now().date(), datetime.now().date(), None],
            [
                "Not Started",
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
    @pytest.mark.usefixtures("department", "user", "analysis_code")
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

        analysis_code = models.AnalysisCode.objects.get(code="1234")
        funding_A = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
        )
        funding_B = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G56789",
            analysis_code=analysis_code,
            budget=5000.00,
        )
        total_effort = funding_A.effort + funding_B.effort
        assert project.total_effort == total_effort

    @pytest.mark.django_db
    def test_percent_effort_left(self, project, analysis_code):
        """Test the percent_effort_left method."""
        from main import models

        # Check when there is no Funding objrect
        assert project.percent_effort_left is None

        # Create Funding object and Monthly Charge
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            funding_body="Funding body",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            expiry_date=datetime.now().date() + timedelta(days=42),
            budget=1000.00,
            daily_rate=200.00,
        )
        models.MonthlyCharge.objects.create(
            date=datetime.today().date(),
            project=project,
            funding=funding,
            amount=100.00,
        )
        assert project.days_left[1] == project.percent_effort_left

    @pytest.mark.django_db
    def test_days_left(self, user, department, analysis_code):
        """Test the days_left method."""
        from main import models

        # Get start and end date as 1st last month-1st current month
        today = datetime.today().date()
        end_date = today.replace(day=1)
        start_date = (end_date - timedelta(days=1)).replace(day=1)
        start_time = datetime.combine(start_date, datetime.min.time())

        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
            start_date=start_date,
            end_date=end_date,
            status="Active",
            charging="Actual",
        )

        # Check days_left is None when no funding assigned
        assert project.days_left is None

        # Create multiple funding objects
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
            daily_rate=50.00,
            expiry_date=end_date,
        )  # 200 days total
        funding.refresh_from_db()

        # Check days_left when there are no time entries
        assert project.days_left == (200, 100)

        # Create some time entries
        models.TimeEntry.objects.create(
            user=user,
            project=project,
            start_time=start_time,
            end_time=start_time + timedelta(hours=3.5),
        )  # 3.5 hours total (0.5 days)

        models.TimeEntry.objects.create(
            user=user,
            project=project,
            start_time=start_time,
            end_time=start_time + timedelta(hours=14),
        )  # 14 hours total (2 days)

        # Check days_left has been updated
        left = funding.effort - 2.5
        days_left = round(left, 1), round(left / project.total_effort * 100, 1)
        assert project.days_left == days_left

    @pytest.mark.parametrize(
        ["status", "start_date", "end_date", "output"],
        [
            ["Draft", None, None, None],
            [
                "Active",
                date(2025, 7, 1),
                date(2025, 8, 14),
                27,
            ],
        ],
    )
    def test_total_working_days(
        self, user, department, project, status, start_date, end_date, output
    ):
        """Test calculation of total working days for projects."""
        from main import models

        project = models.Project.objects.create(
            name="Project",
            department=department,
            lead=user,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        assert project.total_working_days == output

    @pytest.mark.django_db
    @pytest.mark.usefixtures("department", "user", "analysis_code")
    def test_effort_per_day(self):
        """Test calculation of effort per day."""
        from main import models

        department = models.Department.objects.get(name="ICT")
        user = models.User.objects.get(username="testuser")
        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
            status="Active",
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(7),
        )
        assert project.effort_per_day is None

        analysis_code = models.AnalysisCode.objects.get(code="1234")
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=1000.00,
            daily_rate=100.00,
        )
        total_effort = funding.budget / funding.daily_rate
        effort_per_day = total_effort / project.total_working_days
        assert project.effort_per_day == effort_per_day


class TestFunding:
    """Tests for the funding model."""

    def test_model_str(self):
        """Test the object string for the funding model."""
        from main import models

        project = models.Project(name="ProCAT")
        funding = models.Funding(
            project=project, budget=10000.00, cost_centre="centre", activity="G12345"
        )
        assert str(funding) == "ProCAT - £10000.00 - centre_G12345"

    def test_project_code(self):
        """Test project code generated from cost centre and activity."""
        from main import models

        funding = models.Funding()
        assert funding.project_code is None

        funding = models.Funding(cost_centre="centre", activity="G12345")
        assert funding.project_code == "centre_G12345"

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
        analysis_code = models.AnalysisCode(
            code="1234", description="Some code", notes="None"
        )

        funding = models.Funding(
            source="External",
            funding_body="EPSRC",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            expiry_date=datetime.now().date(),
        )
        funding.clean()

    @pytest.mark.parametrize(
        ["activity", "expectation"],
        [
            ["R12345", pytest.raises(ValidationError)],
            ["G1234", pytest.raises(ValidationError)],
            ["G123!5", pytest.raises(ValidationError)],
            ["G12345", does_not_raise()],
        ],
    )
    def test_clean_activity(self, activity, expectation, project, analysis_code):
        """Test the clean method for validation of the activity code."""
        from main import models

        funding = models.Funding(
            project=project,
            source="External",
            funding_body="EPSRC",
            cost_centre="centre",
            activity=activity,
            analysis_code=analysis_code,
            expiry_date=datetime.now().date(),
            budget=38900.00,
            daily_rate=389.00,
        )
        with expectation:
            funding.clean()

    @pytest.mark.parametrize(
        ["budget", "expectation"],
        [
            [-1000.00, pytest.raises(ValidationError)],
            [0.00, does_not_raise()],
            [1000.00, does_not_raise()],
        ],
    )
    def test_budget(self, project, analysis_code, budget, expectation):
        """Test that the budget cannot be a negative value."""
        from main import models

        funding = models.Funding.objects.create(
            project=project,
            source="External",
            funding_body="EPSRC",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
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
    def test_daily_rate(self, project, analysis_code, daily_rate, expectation):
        """Test that the daily rate cannot be a negative value."""
        from main import models

        funding = models.Funding(
            project=project,
            source="External",
            funding_body="EPSRC",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            expiry_date=datetime.now().date(),
            budget=1000.00,
            daily_rate=daily_rate,
        )
        with expectation:
            funding.full_clean()

    @pytest.mark.django_db
    def test_funding_left(self, project, funding):
        """Test the funding_left property."""
        from main import models

        # No monthly charges
        funding.refresh_from_db()
        assert funding.funding_left == funding.budget

        # Check when monthly charge created
        charge_date = funding.expiry_date - timedelta(days=5)
        monthly_charge = models.MonthlyCharge.objects.create(
            project=project, funding=funding, amount=100.00, date=charge_date
        )
        monthly_charge.refresh_from_db()
        assert funding.funding_left == funding.budget - monthly_charge.amount

    def test_effort_left(self, project, funding):
        """Test the effort_left property."""
        from main import models

        # No monthly charges
        funding.refresh_from_db()
        assert round(funding.effort_left) == funding.effort

        # Check when monthly charge created
        charge_date = funding.expiry_date - timedelta(days=5)
        monthly_charge = models.MonthlyCharge.objects.create(
            project=project, funding=funding, amount=100.00, date=charge_date
        )
        monthly_charge.refresh_from_db()
        effort_left = float(
            (funding.budget - monthly_charge.amount) / funding.daily_rate
        )
        assert funding.effort_left == round(effort_left, 1)

    @pytest.mark.django_db
    def test_monthly_pro_rata_charge_is_none(self, user, department, analysis_code):
        """Test the monthly_pro_rata_charge property."""
        from main import models

        project = models.Project.objects.create(
            name="Invalid project",
            department=department,
            lead=user,
            charging="Actual",
        )
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
        )
        assert funding.monthly_pro_rata_charge is None

    @pytest.mark.django_db
    def test_monthly_pro_rata_charge(self, user, department, analysis_code):
        """Test the monthly_pro_rata_charge property."""
        start_date = date(2025, 3, 15)
        end_date = date(2025, 7, 8)  # 5 equal monthly charges will be created
        from main import models

        project = models.Project.objects.create(
            name="Invalid project",
            department=department,
            lead=user,
            charging="Pro-rata",
            start_date=start_date,
            end_date=end_date,
        )
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
        )
        expected_charge = funding.budget / 5
        assert funding.monthly_pro_rata_charge == expected_charge


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
        ["value", "expectation"],
        [
            [-0.5, pytest.raises(ValidationError)],
            [0.0, does_not_raise()],
            [0.5, does_not_raise()],
            [1.0, does_not_raise()],
            [1.5, pytest.raises(ValidationError)],
        ],
    )
    def test_value(self, user, value, expectation):
        """Test that the value of capacity can only between 0 and 1."""
        from main import models

        capacity = models.Capacity(
            user=user, value=value, start_date=datetime.now().date()
        )
        with expectation:
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


class TestMonthlyCharge:
    """Tests for the monthly charge model."""

    def test_model_str(self, project, funding):
        """Test the object string for the monthly charge model."""
        from main import models

        monthly_charge = models.MonthlyCharge(
            project=project, funding=funding, amount=500.00, date=datetime.now().date()
        )
        monthly_charge.clean()
        assert str(monthly_charge) == (
            f"RSE Project {project} ({funding.cost_centre}_{funding.activity}): "
            f"{datetime.now().month}/{datetime.now().year} [rcs-manager@imperial.ac.uk]"
        )

        monthly_charge = models.MonthlyCharge(
            description="A custom description.",
        )
        assert str(monthly_charge) == "A custom description."

    @pytest.mark.parametrize(
        ["amount", "expectation"],
        [
            [-1.00, pytest.raises(ValidationError)],
            [0.00, does_not_raise()],
            [1.00, does_not_raise()],
        ],
    )
    def test_amount(self, project, funding, amount, expectation):
        """Test that the amount must be non-negative."""
        from main import models

        monthly_charge = models.MonthlyCharge(
            project=project, funding=funding, amount=amount, date=datetime.now().date()
        )
        with expectation:
            monthly_charge.full_clean()

    @pytest.mark.usefixtures("project")
    def test_clean_missing_funding_fields(self, project):
        """Test the model validation for the funding fields."""
        from main import models

        funding = models.Funding(cost_centre="centre", activity="G12345")
        monthly_charge = models.MonthlyCharge(
            project=project, funding=funding, amount=10, date=datetime.now().date()
        )
        with pytest.raises(
            ValidationError,
            match="Funding source must have an expiry date.",
        ):
            monthly_charge.clean()

    @pytest.mark.usefixtures("project", "funding")
    def test_clean_invalid_date(self, project, funding):
        """Test the model validation for the date field."""
        from main import models

        monthly_charge = models.MonthlyCharge(
            project=project,
            funding=funding,
            date=funding.expiry_date + timedelta(1),  # invalid date
            amount=funding.funding_left - 1,
        )

        with pytest.raises(
            ValidationError,
            match="Monthly charge must not exceed the funding date or amount.",
        ):
            monthly_charge.clean()

    @pytest.mark.django_db
    def test_clean_invalid_funding(self, project, funding):
        """Test the model validation for the amount field."""
        from main import models

        monthly_charge = models.MonthlyCharge.objects.create(
            project=project,
            funding=funding,
            date=funding.expiry_date - timedelta(1),
            amount=funding.funding_left + 1,  # Invalid funding
        )
        funding.refresh_from_db()  # Update funding object

        with pytest.raises(
            ValidationError,
            match="Monthly charge must not exceed the funding date or amount.",
        ):
            monthly_charge.clean()

    @pytest.mark.usefixtures("funding")
    def test_clean_invalid_description(self, funding):
        """Test the model validation for the missing description field."""
        from main import models

        project = models.Project(name="Project", charging="Manual")
        monthly_charge = models.MonthlyCharge(
            project=project,
            funding=funding,
            amount=funding.funding_left - 1,
            date=funding.expiry_date - timedelta(1),
        )

        with pytest.raises(
            ValidationError,
            match="Line description needed for manual charging method.",
        ):
            monthly_charge.clean()

    @pytest.mark.usefixtures("funding")
    def test_clean_valid(self, project, funding):
        """Test the model validation for valid amount, date and description fields."""
        from main import models

        project = models.Project(name="Project", charging="Manual")
        monthly_charge = models.MonthlyCharge(
            project=project,
            funding=funding,
            amount=funding.funding_left - 1,
            date=funding.expiry_date - timedelta(1),
            description="A custom description.",
        )
        monthly_charge.clean()
