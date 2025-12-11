"""Tests for the models."""

from contextlib import nullcontext as does_not_raise
from datetime import date, datetime, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


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

    def test_clean_when_tentative(self):
        """Test the clean method."""
        from main import models

        project = models.Project(name="ProCAT")
        project.clean()

    def test_clean_when_not_tentative(self, user):
        """Test the clean method."""
        from main import models

        # Mandatory fields are present
        project = models.Project(name="ProCAT", status="Finished")
        with pytest.raises(
            ValidationError,
            match="All fields are mandatory except if Project status is 'Tentative'"
            " or 'Not done'.",
        ):
            project.clean()

        # The end date is after the start date
        project = models.Project(
            name="ProCAT",
            lead=user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            status="Finished",
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
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
            status="Finished",
        )
        project.clean()

    def test_clean_when_project_active(self, user, department):
        """Test the clean method."""
        from main import models

        # All good, the project is tentative.
        project = models.Project(
            name="ProCAT",
            lead=user,
            department=department,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
            status="Tentative",
        )
        project.clean()

        # Change to active but no pk value
        project.status = "Active"
        project.clean()

        # No funding, no active
        project.save()
        with pytest.raises(
            ValidationError,
            match="Active and Confirmed projects must have at least 1 funding source.",
        ):
            project.clean()

        # Add funding source, but it is incomplete, so still fails
        funding, _ = models.Funding.objects.get_or_create(
            project=project,
            source="External",
            budget=10000.00,
        )
        with pytest.raises(
            ValidationError,
            match="Funding of Active and Confirmed projects must be complete.",
        ):
            project.clean()

        # Now things work, as the above is enough for an internal source to be complete
        funding.source = "Internal"
        funding.save()
        project.clean()

    @pytest.mark.parametrize(
        ["status", "start_date", "end_date", "output"],
        [
            ["Tentative", None, None, None],
            ["Confirmed", timezone.now().date(), None, None],
            ["Confirmed", None, timezone.now().date(), None],
            ["Tentative", timezone.now().date(), timezone.now().date(), None],
            [
                "Confirmed",
                timezone.now().date(),
                timezone.now().date() + timedelta(days=1),
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
    def test_total_funding_left(self, project, analysis_code):
        """Test the total_funding_left method."""
        from main import models

        # Check when there is no Funding object
        assert project.total_funding_left is None

        # Create Funding object and Monthly Charges
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            funding_body="Funding body",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            expiry_date=timezone.now().date() + timedelta(days=42),
            budget=1000.00,
            daily_rate=200.00,
        )
        monthly_charge_A = models.MonthlyCharge.objects.create(
            date=timezone.now().date(),
            project=project,
            funding=funding,
            amount=100.00,
            status="Confirmed",
        )
        monthly_charge_B = models.MonthlyCharge.objects.create(
            date=timezone.now().date(),
            project=project,
            funding=funding,
            amount=200.00,
            status="Confirmed",
        )
        models.MonthlyCharge.objects.create(
            date=timezone.now().date(),
            project=project,
            funding=funding,
            amount=300.00,
            status="Draft",  # not counted
        )

        expected_funding_left = (
            funding.budget - monthly_charge_A.amount - monthly_charge_B.amount
        )

        assert project.total_funding_left == expected_funding_left

    @pytest.mark.django_db
    def test_percent_effort_left(self, project, analysis_code):
        """Test the percent_effort_left method."""
        from main import models

        # Check when there is no Funding object
        assert project.percent_effort_left is None

        # Create Funding object and Monthly Charge
        funding = models.Funding.objects.create(
            project=project,
            source="External",
            funding_body="Funding body",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            expiry_date=timezone.now().date() + timedelta(days=42),
            budget=1000.00,
            daily_rate=200.00,
        )
        models.MonthlyCharge.objects.create(
            date=timezone.now().date(),
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
        today = timezone.now().date()
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
            ["Tentative", None, None, None],
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
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(7),
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
        assert funding.project_code == "None"

        funding = models.Funding(cost_centre="centre", activity="G12345")
        assert funding.project_code == "centre_G12345"

    def test_effort(self):
        """Test effort calculated from budget and daily rate."""
        from main import models

        funding = models.Funding(budget=10000.00, daily_rate=389.00)
        assert funding.effort == 25.7

    def test_is_complete_when_internal(self):
        """Test the is_complete method."""
        from main import models

        funding = models.Funding(source="Internal")
        assert funding.is_complete()

    def test_is_complete_when_external(self):
        """Test the is_complete method."""
        from main import models

        # test with missing fields
        funding = models.Funding(source="External")
        assert not funding.is_complete()

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
            expiry_date=timezone.now().date(),
        )
        funding.is_complete()

    def test_clean(self):
        """Test the clean method."""
        from main import models

        # All good, as the project is Tentative
        project = models.Project(name="ProCAT")
        funding = models.Funding(
            project=project,
            budget=10000.00,
            cost_centre="centre",
            activity="G12345",
            source="External",
        )
        funding.clean()

        # Project is Active, so funding must be complete
        funding.project.status = "Active"
        with pytest.raises(ValidationError):
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
            expiry_date=timezone.now().date(),
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
            expiry_date=timezone.now().date(),
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
            expiry_date=timezone.now().date(),
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
            project=project,
            funding=funding,
            amount=100.00,
            date=charge_date,
            status="Confirmed",
        )
        # Create Draft monthly charge (should not be counted)
        models.MonthlyCharge.objects.create(
            project=project,
            funding=funding,
            amount=200.00,
            date=charge_date,
            status="Draft",
        )
        monthly_charge.refresh_from_db()
        assert funding.funding_left == funding.budget - monthly_charge.amount

    def test_effort_left(self, project, funding):
        """Test the effort_left property."""
        from main import models

        # No monthly charges
        funding.refresh_from_db()
        assert funding.effort_left == funding.effort

        # Check when monthly charge created
        charge_date = funding.expiry_date - timedelta(days=5)
        monthly_charge = models.MonthlyCharge.objects.create(
            project=project,
            funding=funding,
            amount=100.00,
            date=charge_date,
            status="Confirmed",
        )
        # Create Draft monthly charge (should not be counted)
        models.MonthlyCharge.objects.create(
            project=project,
            funding=funding,
            amount=200.00,
            date=charge_date,
            status="Draft",
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
            user=user, value=0.5, start_date=timezone.now().date()
        )
        assert (
            str(capacity)
            == f"From {timezone.now().date()}, the capacity of {user!s} is 0.5."
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
            user=user, value=value, start_date=timezone.now().date()
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
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=7.5),
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
            project=project, funding=funding, amount=500.00, date=timezone.now().date()
        )
        monthly_charge.clean()
        assert str(monthly_charge) == (
            f"RSE Project {project} ({funding.cost_centre}_{funding.activity}): "
            f"{timezone.now().month}/{timezone.now().year} [rcs-manager@imperial.ac.uk]"
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
            project=project, funding=funding, amount=amount, date=timezone.now().date()
        )
        with expectation:
            monthly_charge.full_clean()

    @pytest.mark.usefixtures("project")
    def test_clean_missing_funding_fields(self, project):
        """Test the model validation for the funding fields."""
        from main import models

        funding = models.Funding(cost_centre="centre", activity="G12345")
        monthly_charge = models.MonthlyCharge(
            project=project, funding=funding, amount=10, date=timezone.now().date()
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
            status="Confirmed",
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


class TestProjectPhase:
    """Tests for the Project Phase model."""

    def test_model_str(self, project_static):
        """Test the object string for the monthly charge model."""
        from main import models

        project_phase = models.ProjectPhase(
            project=project_static,
            value=1,
            start_date=datetime(2025, 1, 1).date(),
            end_date=datetime(2025, 1, 3).date(),
        )
        project_phase.clean()
        assert str(project_phase) == (
            f"{project_static.name} - {project_phase.start_date} -> "
            f"{project_phase.end_date}"
        )

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "days,start_date,end_date,value,validation_error",
        (
            pytest.param(
                220,
                datetime(2025, 1, 1).date(),
                datetime(2026, 1, 1).date(),
                1,
                None,
                id="1 year, v=1",
            ),
            pytest.param(
                55,
                datetime(2025, 1, 1).date(),
                datetime(2025, 7, 1).date(),
                55 / (181 * 220 / 365),
                None,
                id="6 months, v≈0.5",
            ),
            pytest.param(
                -220,
                datetime(2025, 1, 1).date(),
                datetime(2025, 6, 1).date(),
                None,
                "The FTE value must be greater than or equal to zero.",
                id="FTE < 0",
            ),
            pytest.param(
                220,
                datetime(2026, 1, 1).date(),
                datetime(2025, 1, 1).date(),
                None,
                "The end date must be after the start date.",
                id="End before start",
            ),
        ),
    )
    def test_from_days(
        self, project_static, days, start_date, end_date, value, validation_error
    ):
        """Test the from_days function and that value is calculated correctly."""
        from main import models

        models.ProjectPhase.from_days(
            days, start_date, end_date, project=project_static
        )
        phase = models.ProjectPhase.objects.last()

        if validation_error is not None:
            with pytest.raises(ValidationError, match=validation_error):
                phase.clean()

        else:
            phase.clean()
            assert phase.value == value

    @pytest.mark.parametrize(
        "value,start_date,end_date,expected_days",
        (
            pytest.param(
                1,
                datetime(2025, 1, 1).date(),
                datetime(2026, 1, 1).date(),
                220,
                id="1 year @ 1 FTE",
            ),
            pytest.param(
                0.5,
                datetime(2025, 1, 1).date(),
                datetime(2026, 1, 1).date(),
                110,
                id="181 days @ 0.5 FTE",
            ),
            pytest.param(
                2.3,
                datetime(2025, 7, 1).date(),
                datetime(2026, 8, 16).date(),
                570,
                id="1 year & 46 days @ 2.3 FTE",
            ),
        ),
    )
    def test_days(self, phase, value, start_date, end_date, expected_days):
        """Test the calculation of working days in the project phase."""
        phase.value = value
        phase.start_date = start_date
        phase.end_date = end_date

        assert phase.days == expected_days

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error",
        (
            pytest.param(
                1,
                datetime(2024, 12, 30).date(),
                datetime(2026, 1, 1).date(),
                "Phase period must be within the project period: 2025-01-01 ->"
                " 2027-06-30",
                id="Phase not within project period",
            ),
        ),
    )
    def test_check_phase_in_project(
        self, project_static, phase, value, start_date, end_date, validation_error
    ):
        """Test the check_phase_in_project method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        if validation_error is not None:
            with pytest.raises(
                ValidationError,
                match=validation_error,
            ):
                phase.check_phase_in_project()

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error",
        (
            pytest.param(
                1,
                datetime(2027, 3, 9).date(),
                datetime(2027, 4, 2).date(),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-02-10 -> "
                "2027-03-09 vs. 2027-03-09 -> 2027-04-02",
                id="Overlaps with another phase - end date",
            ),
            pytest.param(
                1,
                datetime(2027, 2, 27).date(),
                datetime(2027, 4, 2).date(),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-02-10 -> "
                "2027-03-09 vs. 2027-02-27 -> 2027-04-02",
                id="Overlaps with another phase - start in phase",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 28).date(),
                datetime(2027, 5, 10).date(),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-04-10 -> "
                "2027-06-30 vs. 2027-03-28 -> 2027-05-10",
                id="Overlaps with another phase - end in phase",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 28).date(),
                datetime(2027, 4, 10).date(),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-04-10 -> "
                "2027-06-30 vs. 2027-03-28 -> 2027-04-10",
                id="Overlaps with another phase - start date",
            ),
        ),
    )
    def test_check_overlapping_phases(
        self, project_static, phase, value, start_date, end_date, validation_error
    ):
        """Test the check_overlapping_phases method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        if validation_error is not None:
            with pytest.raises(
                ValidationError,
                match=validation_error,
            ):
                phase.check_overlapping_phases()

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error",
        (
            pytest.param(
                1,
                datetime(2025, 1, 2).date(),
                datetime(2025, 1, 6).date(),
                "Phase period must align with the start or end of a project or phase.",
                id="Not touching any start/end date",
            ),
        ),
    )
    def test_check_phase_alignment(
        self, project_static, phase, value, start_date, end_date, validation_error
    ):
        """Test the check_phase_alignment method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        if validation_error is not None:
            with pytest.raises(
                ValidationError,
                match=validation_error,
            ):
                phase.check_phase_alignment()

    def test_check_project_funding(self, project):
        """Test the clean method."""
        from main import models

        phase = models.ProjectPhase(
            project=project,
            value=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=12),
        )

        with pytest.raises(
            ValidationError,
            match="Project must have associated funding before phases can be added.",
        ):
            phase.check_project_funding()

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error",
        (
            pytest.param(
                1,
                datetime(2025, 1, 1).date(),
                datetime(2026, 1, 1).date(),
                None,
                id="No err - touching project start",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 20).date(),
                datetime(2027, 4, 9).date(),
                None,
                id="No err - touching a phase start (2027-04-10)",
            ),
            pytest.param(
                1,
                datetime(2025, 3, 10).date(),
                datetime(2026, 4, 6).date(),
                None,
                id="No err - touching a phase end (2027-03-09)",
            ),
            pytest.param(
                1,
                datetime(2025, 3, 10).date(),
                datetime(2026, 4, 9).date(),
                None,
                id="No err - touching a phase start and end (2027-04-10)->(2027-03-09)",
            ),
            pytest.param(
                -1.4,
                datetime(2025, 1, 1).date(),
                datetime(2025, 6, 1).date(),
                "The FTE value must be greater than or equal to zero.",
                id="FTE less than 0",
            ),
            pytest.param(
                1,
                datetime(2026, 1, 1).date(),
                datetime(2025, 1, 1).date(),
                "The end date must be after the start date.",
                id="End before start",
            ),
        ),
    )
    def test_clean(
        self, project_static, phase, value, start_date, end_date, validation_error
    ):
        """Test the clean method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        if validation_error is not None:
            with pytest.raises(
                ValidationError,
                match=validation_error,
            ):
                phase.clean()
