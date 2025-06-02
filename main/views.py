"""Views for the main app."""

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ChoiceField, ModelForm, SelectMultiple
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from . import forms, models, tables


def index(request: HttpRequest) -> HttpResponse:
    """View that renders the index page."""
    return render(request=request, template_name="main/index.html")


class RegistrationView(CreateView):  # type: ignore [type-arg]
    """View to register new users.

    TODO: This is a placeholder for development. When SSO is implemented, this won't be
    needed since available users will be retrieved automatically.
    """

    form_class = forms.CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"


class ProjectsListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    """View to display the list of projects."""

    model = models.Project
    table_class = tables.ProjectTable
    template_name = "main/projects.html"
    filterset_fields = ("nature", "department", "status", "charging")


class FundingListView(LoginRequiredMixin, SingleTableMixin, ListView):  # type: ignore [type-arg]
    """View to display the funding list for all projects."""

    model = models.Funding
    table_class = tables.FundingTable
    template_name = "main/funding.html"


class CapacitiesListView(LoginRequiredMixin, SingleTableMixin, FilterView):
    """View to display the list of capacities."""

    model = models.Capacity
    table_class = tables.CapacityTable
    template_name = "main/capacities.html"
    filterset_fields = ("user",)


class ProjectDetailView(LoginRequiredMixin, UpdateView):
    """Detail view based on a read-only form view.

    While there is a generic Detail View, it is not rendered nicely easily as the
    bootstrap theme needs to be applied on a field by field basis. So we use a form view
    instead, which can easily be styled, and make the form read only.
    """

    fields = "__all__"  # type: ignore [assignment]
    model = models.Project
    template_name = "main/project_detail.html"

    def get_form(self, form_class: Any | None = None) -> ModelForm:  # type: ignore
        """Customize form to add a funding field and make it read-only.

        Args:
            form_class: The form class to use, if any.

        Return:
            A form associated to the model.
        """
        form = super().get_form(form_class)
        funding_summary = self.get_object().funding_summary
        if funding_summary:
            form.fields["Funding sources"] = ChoiceField(
                choices=funding_summary, widget=SelectMultiple
            )

        for field in form.fields.keys():
            form.fields[field].widget.attrs["disabled"] = True
            form.fields[field].widget.attrs["readonly"] = True

        return form

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add project name to the context, so it is easy to retrieve."""
        context = super().get_context_data(**kwargs)
        context["project_name"] = self.get_object().name
        return context


class FundingDetailView(LoginRequiredMixin, UpdateView):
    """View to view details of project funding."""

    fields = "__all__"  # type: ignore [assignment]
    model = models.Funding
    template_name = "main/funding_detail.html"

    def get_form(self, form_class: Any | None = None) -> ModelForm:  # type: ignore
        """Customize form to make it read-only.

        Args:
            form_class: The form class to use, if any.

        Return:
            A form associated to the model.
        """
        form = super().get_form(form_class)

        for field in form.fields.keys():
            form.fields[field].widget.attrs["disabled"] = True
            form.fields[field].widget.attrs["readonly"] = True

        return form

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add funding name to the context, so it is easy to retrieve."""
        context = super().get_context_data(**kwargs)
        context["funding_name"] = str(self.get_object())
        return context
