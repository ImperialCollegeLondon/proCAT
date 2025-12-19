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

        assert project.warnings == ["No funding defined for the project."]
        assert project.has_warnings

    def test_warn_phase_lifetime(self, project_static, phase):
        """Tests Warning model mixin for phase lifetime warnings.

        This includes a patch increasing the `value` of one phase to cover the project
        days and avoid triggering the `_warn_phase_days` warning.
        """
        from main import models

        project_static = models.Project.objects.get(name="ProCATv2")

        # Patch first phase to have a value which passes phase days warning
        models.ProjectPhase.objects.filter(pk=1).update(value=10.9)

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

        assert project.warnings == ["Project days (25) do not match Phase days (23)."]
        assert project.has_warnings
