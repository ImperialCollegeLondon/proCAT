"""Tests for the forms module."""

from datetime import date

import pytest

from main import forms


@pytest.mark.django_db
class TestProjectPhaseForm:
    """Tests for the ProjectPhaseForm."""

    def test_create_sets_value_from_days(self, project_static):
        """Creating a phase via the form should compute 'value' from 'days'."""
        form = forms.ProjectPhaseForm(
            data={
                "project": project_static.pk,
                "days": 55,
                "start_date": date(2025, 1, 1),
                "end_date": date(2025, 12, 31),
            }
        )

        assert form.is_valid(), form.errors
        instance = form.save()

        assert instance.days == 55

    def test_update_recomputes_value_from_new_days(self, project_static):
        """Editing an existing phase's 'days' should update 'value' accordingly."""
        from main import models

        instance = models.ProjectPhase.objects.create(
            project=project_static,
            value=0.5,
            start_date=project_static.start_date,
            end_date=date(2025, 12, 31),
        )
        old_value = instance.value
        new_days = instance.days * 2

        form = forms.ProjectPhaseForm(
            instance=instance,
            data={
                "project": instance.project.pk,
                "days": new_days,
                "start_date": instance.start_date,
                "end_date": instance.end_date,
            },
        )

        assert form.is_valid(), form.errors
        instance = form.save()

        assert instance.days == new_days
        assert instance.value != old_value

    def test_initial_days_populated_from_instance(self, phase):
        """The 'days' initial value should reflect the instance's FTE value."""
        form = forms.ProjectPhaseForm(instance=phase)

        assert form.initial["days"] == phase.days
