"""Tests for the forms module."""

from datetime import date

import pytest

from main import forms


def _phase_formset_data(prefix: str, rows: list[dict]) -> dict:
    """Build POST-like data for the ProjectPhaseInlineFormSet management + rows."""
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i, row in enumerate(rows):
        for key, value in row.items():
            if key == "is_maintenance":
                if value:
                    data[f"{prefix}-{i}-{key}"] = "on"
                continue
            data[f"{prefix}-{i}-{key}"] = value
    return data


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


@pytest.mark.django_db
class TestFundingInlineFormSet:
    """Tests for the FundingInlineFormSet."""

    def test_create_two_funding_rows(self, project_static, analysis_code):
        """Two funding rows can be created together for the same project."""
        data = {
            "funding-TOTAL_FORMS": "2",
            "funding-INITIAL_FORMS": "0",
            "funding-MIN_NUM_FORMS": "0",
            "funding-MAX_NUM_FORMS": "1000",
            "funding-0-source": "Internal",
            "funding-0-budget": "1000",
            "funding-0-daily_rate": "389",
            "funding-1-source": "External",
            "funding-1-funding_body": "UKRI",
            "funding-1-cost_centre": "centre",
            "funding-1-activity": "G12345",
            "funding-1-analysis_code": str(analysis_code.pk),
            "funding-1-expiry_date": "2027-01-01",
            "funding-1-budget": "2000",
            "funding-1-daily_rate": "389",
        }

        formset = forms.FundingInlineFormSet(
            data, instance=project_static, prefix="funding"
        )

        assert formset.is_valid(), formset.errors
        formset.save()

        assert project_static.funding_source.count() == 3


@pytest.mark.django_db
class TestProjectPhaseInlineFormSet:
    """Tests for the ProjectPhaseInlineFormSet."""

    def test_two_non_overlapping_aligned_phases_are_valid(self, project_static):
        """Two new phases spanning the project, back-to-back, should validate."""
        data = _phase_formset_data(
            "phase",
            [
                {
                    "days": "110",
                    "start_date": "2025-01-01",
                    "end_date": "2026-06-30",
                },
                {
                    "days": "110",
                    "start_date": "2026-07-01",
                    "end_date": "2027-06-30",
                },
            ],
        )

        formset = forms.ProjectPhaseInlineFormSet(
            data, instance=project_static, prefix="phase"
        )

        assert formset.is_valid(), formset.errors + formset.non_form_errors()
        formset.save()

        assert project_static.phases.count() == 2

    def test_overlapping_phases_are_rejected(self, project_static):
        """Two new, overlapping phases should be rejected as a group."""
        data = _phase_formset_data(
            "phase",
            [
                {
                    "days": "110",
                    "start_date": "2025-01-01",
                    "end_date": "2026-06-30",
                },
                {
                    "days": "110",
                    "start_date": "2026-06-15",
                    "end_date": "2027-06-30",
                },
            ],
        )

        formset = forms.ProjectPhaseInlineFormSet(
            data, instance=project_static, prefix="phase"
        )

        assert not formset.is_valid()
        assert any("must not overlap" in error for error in formset.non_form_errors())
        assert project_static.phases.count() == 0

    def test_two_maintenance_phases_are_rejected(self, project_static):
        """Two new phases both flagged as maintenance should be rejected."""
        data = _phase_formset_data(
            "phase",
            [
                {
                    "days": "110",
                    "start_date": "2025-01-01",
                    "end_date": "2026-06-30",
                    "is_maintenance": True,
                },
                {
                    "days": "110",
                    "start_date": "2026-07-01",
                    "end_date": "2027-06-30",
                    "is_maintenance": True,
                },
            ],
        )

        formset = forms.ProjectPhaseInlineFormSet(
            data, instance=project_static, prefix="phase"
        )

        assert not formset.is_valid()
        assert any(
            "Only one maintenance phase" in error for error in formset.non_form_errors()
        )

    def test_phase_outside_project_bounds_is_rejected_per_row(self, project_static):
        """A phase outside the project period should fail on its own row."""
        data = _phase_formset_data(
            "phase",
            [
                {
                    "days": "10",
                    "start_date": "2020-01-01",
                    "end_date": "2020-01-31",
                },
            ],
        )

        formset = forms.ProjectPhaseInlineFormSet(
            data, instance=project_static, prefix="phase"
        )

        assert not formset.is_valid()
        assert "Phase period must be within the project period" in str(
            formset.forms[0].errors
        )
