"""Tests for the model utils."""


class TestProjectWarnings:
    """Tests for the different combinations of warnings."""

    def test_pass(self, project, funding):
        """Test Warning model mixin for generated warnings."""
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        assert project.warnings == []
        assert not project.has_warnings

    def test_project_has_funding(self, project):
        """Test Warning model mixin for generated warnings."""
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        assert project.warnings == ["No funding defined for the project."]
        assert project.has_warnings
