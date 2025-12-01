"""Forms needed by ProCAT."""

from typing import ClassVar

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from . import models


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
        fields = (
            "project",
            "source",
            "funding_body",
            "cost_centre",
            "activity",
            "analysis_code",
            "expiry_date",
            "budget",
            "daily_rate",
        )
        widgets: ClassVar = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }


class CreateProjectForm(forms.Form):
    """Form to use in the Cost Recovery view."""

    _NATURE = ((0, "Support"), (1, "Standard"))
    _STATUS = (
        (0, "Tentative"),
        ("Confirmed", "Confirmed"),
        ("Active", "Active"),
        ("Finished", "Finished"),
        ("Not done", "Not done"),
    )
    _CHARGING = (
        ("Actual", "Actual"),
        ("Pro-rata", "Pro-rata"),
        ("Manual", "Manual"),
    )

    name = forms.CharField(
        label="Project Name",
        required=True,
        help_text="Name of the project.",
    )
    nature = forms.TypedChoiceField(
        label="Nature",
        choices=_NATURE,
        required=True,
        coerce=int,
        help_text="Nature of the project.  Typically, support projects cannot be "
        "allocated to sprints easily, the work there is more lightweight and ad hoc, "
        "sometimes at short notice.",
    )
    pi = forms.CharField(
        label="Principal Investigator",
        required=True,
        help_text="Name of the principal investigator responsible for the project. "
        "It should be the actual grant holder, not the main point of contact",
    )

    department = forms.TypedChoiceField(
        label="Department",
        choices=Department.objects.values_list(
            "name", flat=True
        ),  # somehow has faculty too
        required=True,
        help_text="The department in which the research project is based, primarily.",
    )
    start_date = forms.DateField(
        label="Start date",
        required=False,
        help_text="Start date for the project.",
    )
    end_date = forms.DateField(
        label="End date",
        required=False,
        help_text="End date for the project.",
    )
    lead = forms.TypedChoiceField(
        label="RSE Lead",
        required=False,
        choices=get_user_model().objects.values_list("username", flat=True),
        help_text="Project lead from the RSE side.",
    )
    status = forms.TypedChoiceField(
        label="Status",
        required=True,
        initial="Tentative",
        choices=_STATUS,
        help_text="Status of the project. Unless the status is 'Tentative' or "
        "'Not done', most other fields are mandatory.",
    )
    charging = forms.TypedChoiceField(
        label="Charging method",
        required=True,
        initial="Actual",
        choices=_CHARGING,
        help_text="Method for charging the costs of the project. 'Actual' is based"
        " on timesheet records. 'Pro-rata' charges the same amount every month. "
        "Finally, in 'Manual' the charges are scheduled manually.",
    )
    # Want to remove?
    # notifications_effort = models.JSONField(
    #     "Summary of effort left notifications",
    #     default=dict,
    #     blank=True,
    #     help_text="Summarises the notifications sent when an effort threshold "
    #     "is crossed and the corresponding dates.",
    # )
    # notifications_weeks = models.JSONField(
    #     "Summary of weeks left notifications",
    #     default=dict,
    #     blank=True,
    #     help_text="Summarises the notifications sent when the weeks threshold "
    #     "is crossed and the corresponding dates.",
    # )
    clockify_id = forms.CharField(
        label="Clockify ID",
        required=False,
        help_text="The ID of the project in Clockify, if applicable.",
    )
