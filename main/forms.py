"""Forms needed by ProCAT."""

from datetime import timedelta
from typing import Any, ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from . import models
from .utils import days_to_fte


class CustomUserCreationForm(UserCreationForm):  # type: ignore [type-arg]
    """Form to create users with the custom User model.

    TODO: This is a placeholder for development. When SSO is implemented, this won't be
    needed since available users will be retrieved automatically.
    """

    class Meta:
        """Meta class for the form."""

        model = get_user_model()
        fields = ("username", "email")


class CostRecoveryForm(forms.Form):
    """Form to use in the Cost Recovery view."""

    _MONTHS = (
        (1, "January"),
        (2, "February"),
        (3, "March"),
        (4, "April"),
        (5, "May"),
        (6, "June"),
        (7, "July"),
        (8, "August"),
        (9, "September"),
        (10, "October"),
        (11, "November"),
        (12, "December"),
    )
    current_year = timezone.now().year
    _YEARS = ((year, str(year)) for year in range(current_year, current_year - 5, -1))

    month = forms.TypedChoiceField(
        choices=_MONTHS,
        label="Month",
        coerce=int,
        initial=timezone.now().month,
        help_text="Month for which to generate the charges report.",
    )
    year = forms.TypedChoiceField(
        choices=_YEARS,
        label="Year",
        coerce=int,
        help_text="Year for which to generate the charges report.",
    )


class ProjectForm(forms.ModelForm):  # type: ignore [type-arg]
    """Form to create and edit Project instances."""

    class Meta:
        """Meta class for the form."""

        model = models.Project
        exclude = ("notifications_effort", "notifications_weeks")
        widgets: ClassVar = {
            "start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "end_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


class ProjectPhaseForm(forms.ModelForm):  # type: ignore [type-arg]
    """Form to create and edit Project Phase instances."""

    days = forms.FloatField(
        min_value=0,
        required=True,
        help_text="Number of days for the phase.",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        """Override init to populate 'days', if available."""
        super().__init__(*args, **kwargs)
        if self.instance.start_date:
            self.initial["days"] = self.instance.days

    def clean(self) -> dict[str, Any] | None:  # type: ignore[explicit-any]
        """Convert the 'days' field into the model's 'value' (FTE) field."""
        cleaned_data = super().clean() or {}

        days = cleaned_data.get("days")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if days is not None and start_date and end_date and end_date > start_date:
            # `end_date` is an inclusive calendar date, hence the `+ timedelta(days=1)`.
            self.instance.value = days_to_fte(
                start_date, end_date + timedelta(days=1), days
            )

        return cleaned_data

    class Meta:
        """Meta class for the form."""

        model = models.ProjectPhase
        fields = ("project", "days", "start_date", "end_date", "is_maintenance")
        widgets: ClassVar = {
            "start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "end_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


class FundingInlineForm(forms.ModelForm):  # type: ignore [type-arg]
    """Form to create and edit a Funding row inline, as part of a Project form.

    The `project` field is left out, since it is supplied automatically by
    the enclosing formset (see `FundingInlineFormSet`).
    """

    class Meta:
        """Meta class for the form."""

        model = models.Funding
        exclude = ("project",)
        widgets: ClassVar = {
            "expiry_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


FundingInlineFormSet = forms.inlineformset_factory(
    models.Project,
    models.Funding,
    form=FundingInlineForm,
    extra=1,
    can_delete=True,
)


class ProjectPhaseInlineForm(ProjectPhaseForm):
    """Form to create and edit a Project Phase row inline, as part of a Project form.

    Identical to `ProjectPhaseForm`, except that:

    - the `project` field is left out, since it is supplied automatically by
      the enclosing formset (see `ProjectPhaseInlineFormSet`);
    - the database-backed sibling checks (phase overlap, alignment, and
      single maintenance phase - see `models.ProjectPhase.clean()`) are
      skipped during the normal per-row validation. Instead,
      `ProjectPhaseInlineFormSetBase.clean()` performs them once, together,
      against the complete, in-memory set of phases being submitted, once all
      rows have passed their individual field-level validation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        """Override init to flag the instance as validated by the formset."""
        super().__init__(*args, **kwargs)
        self.instance._validated_by_formset = True

    class Meta:
        """Meta class for the form."""

        model = models.ProjectPhase
        fields = ("days", "start_date", "end_date", "is_maintenance")
        widgets: ClassVar = {
            "start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "end_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


class ProjectPhaseInlineFormSetBase(forms.BaseInlineFormSet):  # type: ignore [type-arg]
    """Inline formset to create/edit all Project Phases of a Project together.

    Validates the phases as a group (overlap, alignment, single maintenance
    phase) against their complete, in-memory candidate set - i.e. every
    surviving (not deleted, not blank) row, whether new or pre-existing -
    rather than one row at a time against the database. This allows several
    new and/or edited phases to be submitted together in a single request.
    """

    def clean(self) -> None:
        """Validate the whole set of (surviving) phases together."""
        super().clean()

        if any(self.errors):
            # Individual rows already have errors; the group-level checks
            # below need every row's data to already be well-formed.
            return

        candidates = [
            form.instance
            for form in self.forms
            if form not in self.deleted_forms and form.cleaned_data
        ]

        errors: list[str] = []
        for candidate in candidates:
            others = [c for c in candidates if c is not candidate]
            try:
                candidate.check_overlapping_phases(siblings=others)
                candidate.check_phase_alignment(siblings=others)
                candidate.check_only_one_maintenance_phase(siblings=others)
            except ValidationError as e:
                errors.extend(e.messages)

        if errors:
            # De-duplicate while preserving order: the same message can be
            # raised more than once, e.g. the alignment error is identically
            # worded for every phase that fails it.
            raise forms.ValidationError(list(dict.fromkeys(errors)))


ProjectPhaseInlineFormSet = forms.inlineformset_factory(
    models.Project,
    models.ProjectPhase,
    form=ProjectPhaseInlineForm,
    formset=ProjectPhaseInlineFormSetBase,
    extra=1,
    can_delete=True,
)
