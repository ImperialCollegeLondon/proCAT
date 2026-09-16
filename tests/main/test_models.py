"""Tests for the models."""

from contextlib import nullcontext as does_not_raise
from datetime import UTC, date, datetime, timedelta

import pandas as pd
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
            match=r"All fields are mandatory except if Project status is 'Tentative'"
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
            match=r"The end date must be after the start date.",
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

        # Change to 'Active' but pK is None (status not saved yet, cannot create)
        project.status = "Active"
        with pytest.raises(ValidationError, match="cannot be created directly in"):
            project.clean()

        # Set to 'Tentative' and save in database so that `was_active == FALSE` as
        # per the new changes in `clean()`
        project.status = "Tentative"
        project.save()
        # When trying yo update it to 'Active', there will be no funding
        # and an error should occur
        project.status = "Active"
        with pytest.raises(
            ValidationError,
            match="cannot be made Active, Confirmed, or Maintenance",
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
            match="cannot be made Active, Confirmed, or Maintenance",
        ):
            project.clean()

        # Adding `funding.source` is not enough with new restrictions to when
        # projects can become 'Active': there must be at least one phase to
        # change the status of a project to 'Active'
        funding.source = "Internal"
        funding.save()
        # Add phase
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        # Now there should be no warnings anymore.
        assert project.has_warnings is False

        # Test passes when trying to set it to 'Active' now that
        # both funding and phase are enabled
        project.clean()

    def test_clean_when_maintenance_not_two_phases(self, user, department):
        """Reject setting a project to Maintenance without two phases.

        Updating the status of a project to 'Maintenance' without two phases, or
        without one of them marked as the maintenance phase, must not be possible.
        """
        from main import models

        # All good, the project is Tentative
        project = models.Project(
            name="ProCAT",
            lead=user,
            department=department,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
            status="Tentative",
        )
        project.clean()
        project.save()

        # Add funding and one phase so that status can be set to Active
        models.Funding.objects.get_or_create(
            project=project,
            source="Internal",
            budget=10000.00,
        )
        start, end = project.start_date, project.end_date
        phase1 = models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=start,
            end_date=end,
        )
        # Now it can go to Active and no issues
        project.status = "Active"
        project.clean()
        project.save()

        # A project cannot be set to Maintenance without two phases
        project.status = "Maintenance"
        with pytest.raises(
            ValidationError,
            match="set to Maintenance status unless",
        ):
            project.clean()

        # Modify previous phase and add a second phase
        mid = start + timedelta(days=21)
        phase1.end_date = mid
        phase1.value = 1
        phase1.save(update_fields=["end_date", "value"])
        phase2 = models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=mid + timedelta(days=1),
            end_date=end,
        )
        # Assert total number of phases required to set project to Maintenance status
        assert project.phases.count() == 2
        # Assert sum of total working days (not calendar days) is right
        assert sum(p.days for p in project.phases.all()) == pytest.approx(
            project.total_working_days
        )

        # Still cannot be set to Maintenance without a phase marked as such
        with pytest.raises(
            ValidationError,
            match="set to Maintenance status unless",
        ):
            project.clean()

        # Mark the second phase as the maintenance phase
        phase2.is_maintenance = True
        phase2.save(update_fields=["is_maintenance"])

        # Status is still 'Maintenance', check should not fail now
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
                (1 / 7, 100.0),
            ],
        ],
    )
    def test_weeks_to_deadline(self, status, start_date, end_date, output):
        """Test the weeks_to_deadline method."""
        from main import models

        project = models.Project(
            name="ProCAT", status=status, start_date=start_date, end_date=end_date
        )
        assert project.weeks_to_deadline == (
            pytest.approx(output) if output is not None else None
        )

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
    def test_total_effort_active_status(self, department, user, analysis_code):
        """Test the total_effort method for projects in Active status.

        Active projects should use funding as a fallback when no phases have been
        defined yet (e.g. before the very first phase is created), but should use the
        sum of the non-maintenance phases' days once phases exist, excluding any
        phase flagged as the (future) maintenance phase.
        """
        from main import models

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=39)
        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
            start_date=start_date,
            end_date=end_date,
            status="Active",
        )

        # No funding and no phases: total_effort is None.
        assert project.total_effort is None

        funding = models.Funding.objects.create(
            project=project,
            source="External",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
        )

        # No phases yet: falls back to funding.
        assert project.total_effort == funding.effort

        # Add a non-maintenance phase covering the first half of the project.
        mid = start_date + timedelta(days=19)
        phase1 = models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=start_date,
            end_date=mid,
        )

        # Now that a phase exists, total_effort is phase-based, not funding-based.
        assert project.total_effort == pytest.approx(phase1.days)
        assert project.total_effort != funding.effort

        # Add a phase flagged as the (future) maintenance phase for the second half.
        phase2 = models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=mid + timedelta(days=1),
            end_date=end_date,
            is_maintenance=True,
        )

        # The maintenance phase is excluded from the Active total_effort.
        assert project.total_effort == pytest.approx(phase1.days)
        assert project.total_effort != pytest.approx(phase1.days + phase2.days)

    @pytest.mark.django_db
    def test_days_left_active_with_future_maintenance_phase(self, department, user):
        """Test days_left excludes time logged after a future maintenance phase.

        An Active project may already have a phase flagged for a future transition
        to Maintenance. Since total_effort for Active projects excludes that
        phase's days, days_left must also exclude time logged against that future
        period.
        """
        from main import models

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=39)
        mid = start_date + timedelta(days=19)
        maintenance_start = mid + timedelta(days=1)

        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
            start_date=start_date,
            end_date=end_date,
            status="Active",
        )

        phase1 = models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=start_date,
            end_date=mid,
        )
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=maintenance_start,
            end_date=end_date,
            is_maintenance=True,
        )

        # An entry logged before the maintenance phase starts: should count.
        models.TimeEntry.objects.create(
            user=user,
            project=project,
            start_time=datetime.combine(start_date, datetime.min.time()),
            end_time=datetime.combine(start_date, datetime.min.time())
            + timedelta(hours=7),
        )  # 7 hours -> 1 day

        # An entry logged on/after the maintenance phase starts: excluded.
        models.TimeEntry.objects.create(
            user=user,
            project=project,
            start_time=datetime.combine(maintenance_start, datetime.min.time()),
            end_time=datetime.combine(maintenance_start, datetime.min.time())
            + timedelta(hours=14),
        )  # 14 hours -> 2 days, must NOT be counted

        left = phase1.days - 1
        assert project.days_left == pytest.approx((left, left / phase1.days * 100))

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
        days_left = left, left / project.total_effort * 100
        assert project.days_left == pytest.approx(days_left)

    @pytest.mark.parametrize(
        "days_end_phase1, hours_to_log, expected",
        [
            # Each phase has 74 calendar days (inclusive) --> 44.6 working days
            # C1: 26cd elapsed; 47/73=0.644 of cd remain (`expected_days_left` still
            #     uses exclusive calendar days internally) | 44.6wd*0.644=28.7wd
            #     (exp. days left); no_logged_hr -> 44.6-max([44.6-28.7],0)=28.7
            #     --> 28.7*100/44.6=64.4%
            pytest.param(
                -27,
                0,
                (28.716832426346407, 64.38356164383562),
                id="Partly through maintenance",
            ),
            # C2: phase not started, 44.6wd and 100% left
            pytest.param(
                10, 0, (44.602739726027394, 100.0), id="Maintenance not started"
            ),
            # C3: phase has finished, no time remains
            pytest.param(-80, 0, (0, 0.0), id="Maintenance complete"),
            # C4: same as C1 but logged 140h/7=20wd
            #     44.6-max([44.6-28.7],20) | 44.6-20=24.6wd --> 24.6*100/44.6=55.2%
            pytest.param(
                -27,
                140,
                (24.602739726027394, 55.159705159705155),
                id="Partly through with logged time",
            ),
        ],
    )
    def test_days_left_maintenance_phase(
        self, days_end_phase1, hours_to_log, expected, user, department, analysis_code
    ):
        """Test the days_left method for Maintenance projects across phase states.

        At the moment, projects with status "Maintenance" compute days left
        assuming "Maintenance" is the last phase. The maximum of the elapsed pro-rata
        and the actual time logged is used to calculate the days left.
        """
        from main import models

        today = timezone.now().date()
        project_start = today - timedelta(days=100)
        end_phase1 = today + timedelta(days=days_end_phase1)
        project_end = end_phase1 + timedelta(days=74)

        # Start project as "Tentative", they cannot be started as "Active"
        project = models.Project.objects.create(
            name="ProCAT",
            department=department,
            lead=user,
            start_date=project_start,
            end_date=project_end,
            status="Tentative",
            charging="Actual",
        )

        # Add funding
        models.Funding.objects.create(
            project=project,
            source="Internal",
            cost_centre="centre",
            activity="G12345",
            analysis_code=analysis_code,
            budget=10000.00,
            daily_rate=50.00,
            expiry_date=project_end,
        )

        # Create two non-overlapping phases for the duration of the project
        # The last phase is marked as the "Maintenance" phase
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=project_start,
            end_date=end_phase1,
        )
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=end_phase1 + timedelta(days=1),
            end_date=project_end,
            is_maintenance=True,
        )

        # Log time if needed
        if hours_to_log:
            # Add timezone awareness to avoid warnings
            start_time = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            models.TimeEntry.objects.create(
                user=user,
                project=project,
                start_time=start_time,
                end_time=start_time + timedelta(hours=hours_to_log),
            )

        # Set status to "Maintenance"
        project.status = "Maintenance"
        assert project.phases.count() == 2
        assert project.days_left == pytest.approx(expected, abs=0.05)

    @pytest.mark.parametrize(
        ["status", "start_date", "end_date", "output"],
        [
            ["Tentative", None, None, None],
            [
                "Active",
                date(2025, 7, 1),
                date(2025, 8, 14),
                45 / 365 * 220,
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
    def test_fte(self, project):
        """Test the fte method."""
        from main import models

        assert (project.fte() == 0).all()

        models.ProjectPhase.objects.create(
            project=project,
            value=0.5,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        assert (project.fte() == 0.5).all()

        timerange = pd.date_range(
            start=project.start_date, end=project.end_date + timedelta(days=30), tz=UTC
        )  # add extra days to check that FTE is 0 outside of project period
        output = project.fte(timerange)
        assert (
            output.loc[
                pd.Timestamp(project.start_date, tz=UTC) : pd.Timestamp(
                    project.end_date, tz=UTC
                )
            ]
            == 0.5
        ).all()
        assert (output.loc[~output.index.isin(timerange)] == 0).all()

    @pytest.mark.django_db
    def test_no_phases_returns_zero_series(self, project_mid):
        """When no phases exist, the output should be all zeros."""
        timerange = make_timerange(
            start_date=project_mid.start_date, end_date=project_mid.end_date
        )
        result = project_mid._excess_fte(timerange)
        assert (result == 0.0).all()

    @pytest.mark.django_db
    def test_no_excess_returns_zero_series(self, project_mid):
        """When days_left <= expected_left across phases, excess FTE should be zero."""
        from main import models

        timerange = make_timerange(
            start_date=project_mid.start_date, end_date=project_mid.end_date
        )
        models.ProjectPhase.from_days(
            days=project_mid.total_effort,
            start_date=project_mid.start_date,
            end_date=project_mid.end_date,
            project=project_mid,
        )

        # We have consumed most of the time
        now = timezone.now()
        models.TimeEntry.objects.create(
            user=project_mid.lead,
            project=project_mid,
            start_time=now - timedelta(days=project_mid.total_effort + 1),
            end_time=now,
        )

        # days_left[0] will be <= expected_days_left, so no excess
        result = project_mid._excess_fte(timerange)
        assert (result == 0.0).all()

    @pytest.mark.django_db
    def test_excess_returns_positive_fte_from_today_to_end_date(self, project_mid):
        """When days_left > expected_left, a positive FTE is set from now to end."""
        from main import models

        timerange = make_timerange(
            start_date=project_mid.start_date, end_date=project_mid.end_date
        )
        models.ProjectPhase.from_days(
            days=project_mid.total_effort,
            start_date=project_mid.start_date,
            end_date=project_mid.end_date,
            project=project_mid,
        )

        result = project_mid._excess_fte(timerange)

        today = timezone.now()  # Already has tz
        past = result[result.index < pd.Timestamp(today)]
        future = result[
            (result.index >= pd.Timestamp(today))
            & (result.index <= pd.Timestamp(project_mid.end_date, tz=UTC))
        ]

        assert (past == 0.0).all()
        assert (future > 0.0).all()


def make_timerange(
    start_date: datetime | None = None, end_date: datetime | None = None
) -> pd.DatetimeIndex:
    """A simple daily timerange."""
    today = timezone.now()
    start_date = start_date if start_date else today - timedelta(days=10)
    end_date = end_date if end_date else today + timedelta(days=10)

    return pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
        tz=UTC,
    )


class TestDailyRate:
    """Tests for the DailyRate model and get_current_daily_rate."""

    def test_model_str(self):
        """Test the object string for the daily rate model."""
        from main import models

        daily_rate = models.DailyRate(rate=389.00, effective_date=date(2000, 1, 1))
        assert str(daily_rate) == "£389.00 (from 2000-01-01)"

    @pytest.mark.django_db
    def test_get_current_daily_rate_fallback(self):
        """Test the fallback value is used when no DailyRate exists."""
        from main import models

        models.DailyRate.objects.all().delete()
        assert models.get_current_daily_rate() == models.FALLBACK_DAILY_RATE

    @pytest.mark.django_db
    def test_get_current_daily_rate_picks_latest_applicable(self):
        """Test the most recent, non-future, DailyRate is picked."""
        from main import models

        today = timezone.now().date()
        models.DailyRate.objects.create(
            rate=389.00, effective_date=today - timedelta(days=365)
        )
        current = models.DailyRate.objects.create(
            rate=405.00, effective_date=today - timedelta(days=1)
        )
        # Scheduled ahead of time, so should not be picked up yet.
        models.DailyRate.objects.create(
            rate=420.00, effective_date=today + timedelta(days=1)
        )

        assert models.get_current_daily_rate() == current.rate

    @pytest.mark.django_db
    def test_get_current_daily_rate_tie_break_by_pk(self):
        """Test ties on effective_date are broken by the most recently created."""
        from main import models

        today = timezone.now().date()
        models.DailyRate.objects.create(rate=389.00, effective_date=today)
        latest = models.DailyRate.objects.create(rate=405.00, effective_date=today)

        assert models.get_current_daily_rate() == latest.rate


class TestFunding:
    """Tests for the funding model."""

    def test_model_str(self):
        """Test the object string for the funding model."""
        from main import models

        project = models.Project(name="ProCAT")
        funding = models.Funding(
            project=project,
            budget=10000.00,
            cost_centre="centre",
            activity="G12345",
            daily_rate=389.00,
        )
        assert str(funding) == "ProCAT - £10000.00 - centre_G12345"

    @pytest.mark.django_db
    def test_daily_rate_defaults_to_current_standard_rate(self, project):
        """Test that a new Funding defaults to the current standard rate."""
        from main import models

        models.DailyRate.objects.create(
            rate=405.00, effective_date=timezone.now().date()
        )
        funding = models.Funding(project=project, budget=10000.00)
        assert funding.daily_rate == 405.00

    def test_daily_rate_can_be_overridden_with_a_bespoke_rate(self):
        """Test that a Funding can use a rate that differs from the standard one."""
        from main import models

        funding = models.Funding(budget=10000.00, daily_rate=450.00)
        assert funding.daily_rate == 450.00

    def test_project_code(self):
        """Test project code generated from cost centre and activity."""
        from main import models

        funding = models.Funding(daily_rate=389.00)
        assert funding.project_code == "None"

        funding = models.Funding(
            cost_centre="centre", activity="G12345", daily_rate=389.00
        )
        assert funding.project_code == "centre_G12345"

    def test_effort(self):
        """Test effort calculated from budget and daily rate."""
        from main import models

        funding = models.Funding(budget=10000.00, daily_rate=389.00)
        assert funding.effort == pytest.approx(10000.00 / 389.00)

    def test_is_complete_when_internal(self):
        """Test the is_complete method."""
        from main import models

        funding = models.Funding(source="Internal", daily_rate=389.00)
        assert funding.is_complete()

    def test_is_complete_when_external(self):
        """Test the is_complete method."""
        from main import models

        # test with missing fields
        funding = models.Funding(source="External", daily_rate=389.00)
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
            daily_rate=389.00,
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
            daily_rate=389.00,
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
        assert funding.effort_left == pytest.approx(effort_left)

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
        assert funding.monthly_pro_rata_charge(date(2025, 3, 15)) is None

    @pytest.mark.django_db
    def test_monthly_pro_rata_charge(self, user, department, analysis_code):
        """Test the monthly_pro_rata_charge property."""
        start_date = date(2025, 3, 15)
        end_date = date(2025, 7, 8)  # 4 equal monthly charges will be created
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
        expected_charge = funding.budget / 4
        assert funding.monthly_pro_rata_charge(start_date) == expected_charge
        # Last month is not charged, so the charge is None
        assert funding.monthly_pro_rata_charge(end_date) is None


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
            match=r"Funding source must have an expiry date.",
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
            match=r"Monthly charge must not exceed the funding date or amount.",
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
            match=r"Monthly charge must not exceed the funding date or amount.",
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
            match=r"Line description needed for manual charging method.",
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

    def test_trace(self) -> None:
        """Test the trace method."""
        from main import models

        start_date = datetime(2025, 1, 1).date()
        end_date = datetime(2025, 1, 3).date()
        project_phase = models.ProjectPhase(
            value=1,
            start_date=start_date,
            end_date=end_date,
        )
        project_timerange = pd.date_range(start=start_date, end=end_date, tz=UTC)
        assert (project_phase.trace() == 1).all()

        timerange = pd.date_range(
            start=datetime(2024, 12, 1).date(), end=datetime(2025, 2, 1).date(), tz=UTC
        )
        output = project_phase.trace(timerange)
        assert (output.loc[project_timerange] == 1).all()
        assert (output.loc[~output.index.isin(project_timerange)] == 0).all()

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
                datetime(2025, 12, 31).date(),
                1,
                None,
                id="1 year, v=1",
            ),
            pytest.param(
                55,
                datetime(2025, 1, 1).date(),
                datetime(2025, 6, 30).date(),
                55 / (181 * 220 / 365),
                None,
                id="6 months, v≈0.5",
            ),
            pytest.param(
                -220,
                datetime(2025, 1, 1).date(),
                datetime(2025, 6, 1).date(),
                None,
                r"The FTE value must be greater than or equal to zero.",
                id="FTE < 0",
            ),
            pytest.param(
                220,
                datetime(2026, 1, 1).date(),
                datetime(2025, 1, 1).date(),
                None,
                r"The end date must be after the start date.",
                id="End before start",
            ),
        ),
    )
    def test_from_days(
        self, project_static, days, start_date, end_date, value, validation_error
    ):
        """Test the from_days function and that value is calculated correctly."""
        from main import models

        if validation_error is not None:
            with pytest.raises(ValidationError, match=validation_error):
                models.ProjectPhase.from_days(
                    days, start_date, end_date, project=project_static
                )

        else:
            models.ProjectPhase.from_days(
                days, start_date, end_date, project=project_static
            )
            phase = models.ProjectPhase.objects.last()
            assert phase.value == value

    @pytest.mark.parametrize(
        "value,start_date,end_date,expected_days",
        (
            pytest.param(
                1,
                datetime(2025, 1, 1).date(),
                datetime(2025, 12, 31).date(),
                220,
                id="1 year @ 1 FTE",
            ),
            pytest.param(
                0.5,
                datetime(2025, 1, 1).date(),
                datetime(2025, 12, 31).date(),
                110,
                id="181 days @ 0.5 FTE",
            ),
            pytest.param(
                2.3,
                datetime(2025, 7, 1).date(),
                datetime(2026, 8, 16).date(),
                571.1561643835616,
                id="1 year & 46 days @ 2.3 FTE",
            ),
        ),
    )
    def test_days(self, phase, value, start_date, end_date, expected_days):
        """Test the calculation of working days in the project phase."""
        phase.value = value
        phase.start_date = start_date
        phase.end_date = end_date

        assert phase.days == pytest.approx(expected_days)

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error,message",
        (
            pytest.param(
                1,
                datetime(2024, 12, 30).date(),
                datetime(2026, 1, 1).date(),
                pytest.raises(ValidationError),
                "Phase period must be within the project period: 2025-01-01 ->"
                " 2027-06-30",
                id="Phase not within project period",
            ),
            pytest.param(
                1,
                datetime(2025, 12, 30).date(),
                datetime(2026, 1, 1).date(),
                does_not_raise(),
                None,
                id="Phase within project period",
            ),
        ),
    )
    def test_check_phase_in_project(
        self,
        project_static,
        phase,
        value,
        start_date,
        end_date,
        validation_error,
        message,
    ):
        """Test the check_phase_in_project method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        with validation_error as e:
            phase.check_phase_in_project()
        assert message is None or message in str(e)

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error,message",
        (
            pytest.param(
                1,
                datetime(2027, 3, 9).date(),
                datetime(2027, 4, 2).date(),
                pytest.raises(ValidationError),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-02-10 -> "
                "2027-03-09 vs. 2027-03-09 -> 2027-04-02",
                id="Overlaps with another phase - end date",
            ),
            pytest.param(
                1,
                datetime(2027, 2, 27).date(),
                datetime(2027, 4, 2).date(),
                pytest.raises(ValidationError),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-02-10 -> "
                "2027-03-09 vs. 2027-02-27 -> 2027-04-02",
                id="Overlaps with another phase - start in phase",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 28).date(),
                datetime(2027, 5, 10).date(),
                pytest.raises(ValidationError),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-04-10 -> "
                "2027-06-30 vs. 2027-03-28 -> 2027-05-10",
                id="Overlaps with another phase - end in phase",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 28).date(),
                datetime(2027, 4, 10).date(),
                pytest.raises(ValidationError),
                "Phase period must not overlap with other phase periods for the same "
                "project: 2027-04-10 -> "
                "2027-06-30 vs. 2027-03-28 -> 2027-04-10",
                id="Overlaps with another phase - start date",
            ),
            pytest.param(
                1,
                datetime(2027, 1, 1).date(),
                datetime(2027, 1, 10).date(),
                does_not_raise(),
                None,
                id="Doesn't overlap but would fail clean",
            ),
        ),
    )
    def test_check_overlapping_phases(
        self,
        project_static,
        phase,
        value,
        start_date,
        end_date,
        validation_error,
        message,
    ):
        """Test the check_overlapping_phases method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        with validation_error as e:
            phase.check_overlapping_phases()
        assert message is None or message in str(e)

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error,message",
        (
            pytest.param(
                1,
                datetime(2025, 1, 2).date(),
                datetime(2025, 1, 6).date(),
                pytest.raises(ValidationError),
                "Phase period must align with the start or end of a project or phase.",
                id="Not touching any start/end date",
            ),
            pytest.param(
                1,
                datetime(2025, 1, 1).date(),
                datetime(2026, 1, 1).date(),
                does_not_raise(),
                None,
                id="No err - touching project start",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 20).date(),
                datetime(2027, 4, 9).date(),
                does_not_raise(),
                None,
                id="No err - touching a phase start (2027-04-10)",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 10).date(),
                datetime(2027, 4, 6).date(),
                does_not_raise(),
                None,
                id="No err - touching a phase end (2027-03-10)",
            ),
            pytest.param(
                1,
                datetime(2027, 3, 10).date(),
                datetime(2027, 4, 9).date(),
                does_not_raise(),
                None,
                id="No err - touching a phase start and end (2027-03-10)->(2027-04-09)",
            ),
        ),
    )
    def test_check_phase_alignment(
        self,
        project_static,
        phase,
        value,
        start_date,
        end_date,
        validation_error,
        message,
    ):
        """Test the check_phase_alignment method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        with validation_error as e:
            phase.check_phase_alignment()
        assert message is None or message in str(e)

    def test_check_project_funding(self, project):
        """Test the check_project_funding method."""
        from main import models

        phase = models.ProjectPhase(
            project=project,
            value=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=12),
        )

        with pytest.raises(
            ValidationError,
            match=r"Project must have associated funding before phases can be added.",
        ):
            phase.check_project_funding()

    @pytest.mark.parametrize(
        "value,start_date,end_date,validation_error,message",
        (
            pytest.param(
                -1.4,
                datetime(2025, 1, 1).date(),
                datetime(2025, 6, 1).date(),
                pytest.raises(ValidationError),
                "The FTE value must be greater than or equal to zero.",
                id="FTE less than 0",
            ),
            pytest.param(
                1,
                datetime(2026, 1, 1).date(),
                datetime(2025, 1, 1).date(),
                pytest.raises(ValidationError),
                "The end date must be after the start date.",
                id="End before start",
            ),
        ),
    )
    def test_clean(
        self,
        project_static,
        phase,
        value,
        start_date,
        end_date,
        validation_error,
        message,
    ):
        """Test the clean method."""
        from main import models

        phase = models.ProjectPhase(
            project=project_static,
            value=value,
            start_date=start_date,
            end_date=end_date,
        )

        with validation_error as e:
            phase.clean()
        assert message is None or message in str(e)

    def test_before_phase_returns_total_days(self, project_static):
        """When today is before the start date, all days should remain."""
        from main import models

        today = timezone.now()
        phase = models.ProjectPhase(
            project=project_static,
            value=0.7,
            start_date=(today + timedelta(days=10)).date(),
            end_date=(today + timedelta(days=40)).date(),
        )

        assert phase.expected_days_left == phase.days

    def test_after_phase_returns_zero(self, project_static):
        """When today is after the end date, no days should remain."""
        from main import models

        today = timezone.now()
        phase = models.ProjectPhase(
            project=project_static,
            value=0.7,
            start_date=(today - timedelta(days=40)).date(),
            end_date=(today - timedelta(days=10)).date(),
        )

        assert phase.expected_days_left == 0

    def test_midpoint_of_phase_returns_half_days(self, project_static):
        """When today is exactly halfway through, half the days should remain."""
        from main import models

        today = timezone.now()
        phase = models.ProjectPhase(
            project=project_static,
            value=0.7,
            start_date=(today - timedelta(days=40)).date(),
            end_date=(today + timedelta(days=40)).date(),
        )

        assert phase.expected_days_left == phase.days / 2
