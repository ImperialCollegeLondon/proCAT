"""Tests for the model utils."""

from datetime import timedelta

from django.utils import timezone


class TestProjectWarnings:
    """Tests for the different combinations of warnings."""

    def test_pass(self, funding):
        """Test Warning model mixin produces no generated warnings."""
        from main import models
        from main.utils import days_to_fte

        project = models.Project.objects.get(name="ProCAT")

        # Patch project with spanning phase
        fte = days_to_fte(
            project.start_date, project.end_date + timedelta(days=1), funding.effort
        )
        models.ProjectPhase.objects.create(
            project=project,
            value=fte,
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
        """Tests Warning model mixin for phase lifetime warnings."""
        from main import models

        project_static = models.Project.objects.get(name="ProCATv2")

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
            "Project days (25.7) do not match Phase days (23.3)."
        ]
        assert project.has_warnings
