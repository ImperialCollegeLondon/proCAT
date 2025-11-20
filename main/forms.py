"""Forms needed by ProCAT."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone


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
