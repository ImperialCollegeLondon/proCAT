"""Views for the main app."""

from typing import Any

import bokeh
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import Form, ModelForm
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_filters.views import FilterView
from django_tables2 import RequestConfig, SingleTableMixin

from . import forms, models, plots, report, tables


class GroupRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure that the user belongs to specific group(s)."""

    group_name = "RSE"
    raise_exception = True

    def test_func(self):  # type: ignore
        """Check if the user belongs to allowed group(s) or is superuser."""
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name=self.group_name).exists()


class RegistrationView(CreateView):  # type: ignore [type-arg]
    """View to register new users.

    TODO: This is a placeholder for development. When SSO is implemented, this won't be
    needed since available users will be retrieved automatically.
    """

    form_class = forms.CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"


class ProjectsListView(LoginRequiredMixin, FilterView):
    """View to display the list of projects split in five pre-filtered tables."""

    model = models.Project
    template_name = "main/projects.html"
    filterset_fields = ("nature", "department", "status", "charging")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add multiple pre-filtered tables to the context."""
        context = super().get_context_data(**kwargs)

        base_qs = self.get_queryset()

        buckets = [
            ("Active", {"status": "Active"}, "active-"),
            ("Confirmed", {"status": "Confirmed"}, "confirmed-"),
            ("Tentative", {"status": "Tentative"}, "tentative-"),
            ("Finished", {"status": "Finished"}, "finished-"),
            ("Not done", {"status": "Not done"}, "not-done-"),
        ]

        created_tables: list[tuple[str, tables.ProjectTable]] = []
        for title, filt, prefix in buckets:
            qs = base_qs.filter(**filt)
            tbl = tables.ProjectTable(qs, prefix=prefix)
            RequestConfig(self.request).configure(tbl)
            created_tables.append((title, tbl))

        context["tables"] = created_tables
        return context


class FundingListView(
    GroupRequiredMixin,
    LoginRequiredMixin,
    SingleTableMixin,
    ListView,  # type: ignore [type-arg]
):
    """View to display the funding list for all projects."""

    model = models.Funding
    table_class = tables.FundingTable
    template_name = "main/funding.html"
    group_name = "RSE"


class CapacitiesListView(
    GroupRequiredMixin, LoginRequiredMixin, SingleTableMixin, FilterView
):
    """View to display the list of capacities."""

    model = models.Capacity
    table_class = tables.CapacityTable
    template_name = "main/capacities.html"
    filterset_fields = ("user",)
    group_name = "RSE"


class CustomBaseDetailView(LoginRequiredMixin, UpdateView):  # type: ignore [type-arg]
    """Detail view based on a read-only form view.

    While there is a generic Detail View, it is not rendered nicely easily as the
    bootstrap theme needs to be applied on a field by field basis. So we use a form view
    instead, which can easily be styled, and make the form read only.
    """

    fields = "__all__"  # type: ignore [assignment]

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


class ProjectDetailView(CustomBaseDetailView, GroupRequiredMixin):
    """View to view details of a project."""

    model = models.Project
    template_name = "main/project_detail.html"
    group_name = "RSE"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add project name and funding table to the context.

        A custom query is used with the funding table, so only the funding for the
        current project is displayed.
        """
        context = super().get_context_data(**kwargs)
        context["project_name"] = self.get_object().name
        # get funding info for the current project
        funding_source = self.get_object().funding_source.all()
        funding_table = tables.FundingTable(funding_source)
        # enables the table to be sorted by column headings
        RequestConfig(self.request).configure(funding_table)
        context["funding_table"] = funding_table
        return context


class FundingDetailView(CustomBaseDetailView, GroupRequiredMixin):
    """View to view details of project funding."""

    model = models.Funding
    template_name = "main/funding_detail.html"
    group_name = "RSE"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add funding name to the context, so it is easy to retrieve."""
        context = super().get_context_data(**kwargs)
        funding = self.get_object()
        context["funding_name"] = str(funding)

        # Monthly charges table for this funding
        charges_qs = models.MonthlyCharge.objects.filter(funding=funding).order_by(
            "-date"
        )
        charges_table = tables.MonthlyChargeTable(charges_qs)
        RequestConfig(self.request).configure(charges_table)
        context["monthly_charges_table"] = charges_table

        return context


class CapacityPlanningView(LoginRequiredMixin, TemplateView):
    """View that renders the Capacity Planning page."""

    template_name = "main/capacity_planning.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add HTML components and Bokeh version to the context."""
        context = super().get_context_data(**kwargs)
        layout = plots.create_capacity_planning_layout()
        context.update(plots.html_components_from_plot(layout))
        context["bokeh_version"] = bokeh.__version__
        return context


class CostRecoveryView(LoginRequiredMixin, FormView):  # type: ignore [type-arg]
    """View that renders the Cost Recovery page."""

    template_name = "main/cost_recovery.html"
    form_class = forms.CostRecoveryForm

    def form_valid(self, form: Form) -> HttpResponse:
        """Generate csv using the dates provided in the form."""
        month = form.cleaned_data["month"]
        year = form.cleaned_data["year"]
        response = report.create_charges_report_for_download(month, year)
        return response

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add HTML components and Bokeh version to the context."""
        context = super().get_context_data(**kwargs)
        layout = plots.create_cost_recovery_layout()
        context.update(plots.html_components_from_plot(layout))
        context["bokeh_version"] = bokeh.__version__
        return context
