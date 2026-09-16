"""Tests for the model utils."""

from datetime import timedelta

from django.utils import timezone


class TestProjectWarnings:
    """Tests for the different combinations of warnings."""

    def test_pass(self, project, funding):
        """Test Warning model mixin produces no generated warnings."""
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        # Patch project with spanning phase
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
        )

        assert project.warnings == []
        assert not project.has_warnings

    def test_project_has_funding(self, project):
        """Test Warning model mixin for has funding warnings."""
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        # Patch project with spanning phase
        models.ProjectPhase.objects.create(
            project=project,
            value=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
        )
        # `_warn_no_funding` checks for both now, message changed
        assert project.warnings == [
            "No funding defined for the project or incomplete row."
        ]
        assert project.has_warnings

    def test_warn_phase_lifetime(self, project_static, phase):
        """Tests Warning model mixin for phase lifetime warnings.

        This includes a patch increasing the `value` of one phase to cover the project
        days and avoid triggering the `_warn_phase_days` warning.
        """
        from main import models
        from main.utils import days_to_fte

        project_static = models.Project.objects.get(name="ProCATv2")

        # Patch first phase to have a value which passes the phase days warning, i.e.
        # so that the sum of both phases' days matches the project's total working
        # days exactly.
        first_phase = models.ProjectPhase.objects.get(pk=1)
        other_days = sum(
            p.days
            for p in models.ProjectPhase.objects.filter(project=project_static).exclude(
                pk=first_phase.pk
            )
        )
        assert project_static.total_working_days is not None
        needed_days = project_static.total_working_days - other_days
        # `end_date` is inclusive, hence the `+ timedelta(days=1)`, matching how
        # `ProjectPhase.days` computes its own value.
        value = days_to_fte(
            first_phase.start_date,
            first_phase.end_date + timedelta(days=1),
            needed_days,
        )
        models.ProjectPhase.objects.filter(pk=first_phase.pk).update(value=value)

        assert project_static.warnings == ["Phases do not span project lifetime."]
        assert project_static.has_warnings

    def test_warn_phase_days(self, project, funding):
        """Tests Warning model mixin for phase days mismatch warnings."""
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        # Patch project with spanning phase at pass phase lifetime warning
        models.ProjectPhase.objects.create(
            project=project,
            value=0.9,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=42),
        )

        assert project.warnings == [
            "Project days (25.9) do not match Phase days (23.3)."
        ]
        assert project.has_warnings
