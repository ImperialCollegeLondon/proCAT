"""Forms needed by ProCAT."""

from typing import Any, ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
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


class FundingForm(forms.ModelForm):  # type: ignore [type-arg]
    """Form to create and edit funding instances."""

    class Meta:
        """Meta class for the form."""

        model = models.Funding
        fields = "__all__"
        widgets: ClassVar = {
            "expiry_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


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
            self.instance.value = days_to_fte(start_date, end_date, days)

        return cleaned_data

    class Meta:
        """Meta class for the form."""

        model = models.ProjectPhase
        fields = ("project", "days", "start_date", "end_date")
        widgets: ClassVar = {
            "start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "end_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }


class ProjectPhaseDetailForm(forms.ModelForm):  # type: ignore [type-arg]
    """Read-only form to display Project Phase details.

    Adds the 'days' field (not a model field, so it is not shown otherwise) and
    formats it, along with the FTE 'value', to two decimal places for display.
    """

    days = forms.CharField(required=False, help_text="Number of days for the phase.")
    value = forms.CharField(required=False, label="FTE value")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        """Override init to populate 'days' and format 'value' for display."""
        super().__init__(*args, **kwargs)
        if self.instance.start_date and self.instance.end_date:
            self.initial["days"] = f"{self.instance.days:.2f}"
        if self.instance.value is not None:
            self.initial["value"] = f"{self.instance.value:.2f}"

    class Meta:
        """Meta class for the form."""

        model = models.ProjectPhase
        fields = ("project", "days", "value", "start_date", "end_date")
        widgets: ClassVar = {
            "start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "end_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
        }
