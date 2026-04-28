"""Views for the main app."""

from typing import Any

import bokeh
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.forms import Form, ModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_filters.views import FilterView
from django_tables2 import RequestConfig, SingleTableMixin

from . import forms, models, plots, report, tables


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
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SingleTableMixin,
    ListView,  # type: ignore [type-arg]
):
    """View to display the funding list for all projects."""

    permission_required = "main.view_funding"
    raise_exception = False

    model = models.Funding
    table_class = tables.FundingTable
    template_name = "main/funding.html"


class CapacitiesListView(
    LoginRequiredMixin, PermissionRequiredMixin, SingleTableMixin, FilterView
):
    """View to display the list of capacities."""

    permission_required = "main.view_capacity"
    raise_exception = False

    model = models.Capacity
    table_class = tables.CapacityTable
    template_name = "main/capacities.html"
    filterset_fields = ("user",)


class CustomBaseDetailView(LoginRequiredMixin, UpdateView):  # type: ignore [type-arg]
    """Detail view based on a read-only form view.

    While there is a generic Detail View, it is not rendered nicely easily as the
    bootstrap theme needs to be applied on a field by field basis. So we use a form view
    instead, which can easily be styled, and make the form read only.
    """

    fields = "__all__"

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


class ProjectDetailView(PermissionRequiredMixin, CustomBaseDetailView):
    """View to view details of a project."""

    model = models.Project
    template_name = "main/project_detail.html"
    permission_required = "main.view_project"
    raise_exception = False
    fields = None  # type: ignore
    form_class = forms.ProjectForm

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
        project_phase = models.ProjectPhase.objects.filter(
            project__name=self.get_object().name
        )
        phase_table = tables.ProjectPhaseTable(project_phase)
        # enables the table to be sorted by column headings
        RequestConfig(self.request).configure(funding_table)
        RequestConfig(self.request).configure(phase_table)

        context["funding_table"] = funding_table
        context["phase_table"] = phase_table
        return context


class FundingDetailView(PermissionRequiredMixin, CustomBaseDetailView):
    """View to view details of project funding."""

    model = models.Funding
    template_name = "main/funding_detail.html"
    permission_required = "main.view_funding"
    raise_exception = False

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


class FundingCreateView(PermissionRequiredMixin, CreateView):  # type: ignore [type-arg]
    """View to create a new funding."""

    permission_required = "main.create_funding"
    raise_exception = False

    model = models.Funding
    form_class = forms.FundingForm
    template_name = "main/funding_form.html"
    success_url = reverse_lazy("main:funding")


class ProjectCreateView(PermissionRequiredMixin, CreateView):  # type: ignore [type-arg]
    """View to create a new project."""

    permission_required = "main.create_project"
    raise_exception = False

    model = models.Project
    form_class = forms.ProjectForm
    template_name = "main/project_form.html"
    success_url = reverse_lazy("main:projects")


class ProjectUpdateView(PermissionRequiredMixin, UpdateView):  # type: ignore [type-arg]
    """Update view based on a form from the Project model."""

    model = models.Project
    template_name = "main/project_update.html"
    permission_required = "main.change_project"
    raise_exception = False
    form_class = forms.ProjectForm

    def get_success_url(self):  # type: ignore [no-untyped-def]
        """Django magic function to obtain a dynamic success URL."""
        return reverse_lazy("main:project_detail", kwargs={"pk": self.object.pk})


class ProjectPhaseCreateView(PermissionRequiredMixin, CreateView):  # type: ignore [type-arg]
    """View to create a new project phase."""

    permission_required = "main.create_project_phase"
    raise_exception = False

    model = models.ProjectPhase
    form_class = forms.ProjectPhaseForm
    template_name = "main/project_phase_form.html"
    success_url = reverse_lazy("main:projects")


@login_required
@permission_required("main.create_project_phase", raise_exception=True)
def create_default_project_phase(request: HttpRequest) -> HttpResponse:
    """Create a default project phase.

    This view is used to create a default project phase for a project, given the total
    effort in days and the start and end dates of the project.

    If successful, the project detail page will be reloaded to show the new phase. If
    the project does not have a total effort defined, no phase will be created and the
    user will be redirected to the project detail page with no changes.

    Args:
        request: The HTTP request object.

    Returns:
        An HTTP response object that redirects to the project detail page.
    """
    if request.method == "POST":
        project_name = request.POST.get("project_name")
        project = models.Project.objects.get(name=project_name)

        assert project.start_date is not None
        assert project.end_date is not None
        if days := project.total_effort:
            try:
                models.ProjectPhase.from_days(
                    days=days,
                    project=project,
                    start_date=project.start_date,
                    end_date=project.end_date,
                )
            except Exception as e:
                messages.add_message(
                    request,
                    messages.WARNING,
                    e.messages[0]
                    if hasattr(e, "messages") and len(e.messages) > 0
                    else str(e),
                )
        else:
            messages.add_message(
                request,
                messages.WARNING,
                "No funding defined for this project. Please add a funding source"
                "before creating a project phase.",
            )

        return HttpResponseRedirect(
            reverse_lazy("main:project_detail", kwargs={"pk": project.pk})
        )

    else:
        # If GET, we just go back to the detail page without doing anything or to the
        # projects page if the referer is not defined.
        return HttpResponseRedirect(
            request.META.get("HTTP_REFERER", reverse_lazy("main:projects"))
        )


class ProjectPhaseDetailView(PermissionRequiredMixin, CustomBaseDetailView):
    """View to view details of a project."""

    model = models.ProjectPhase
    template_name = "main/project_phase_detail.html"
    permission_required = "main.view_project_phase"
    raise_exception = False

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add project name and funding table to the context.

        A custom query is used with the funding table, so only the funding for the
        current project is displayed.
        """
        context = super().get_context_data(**kwargs)
        context["project_name"] = self.get_object().project.name

        return context


class FundingUpdateView(PermissionRequiredMixin, UpdateView):  # type: ignore [type-arg]
    """Update view based on a form from the Funding model."""

    model = models.Funding
    template_name = "main/funding_update.html"
    permission_required = "main.change_funding"
    raise_exception = False
    form_class = forms.FundingForm

    def get_success_url(self):  # type: ignore [no-untyped-def]
        """Django magic function to obtain a dynamic success URL."""
        return reverse_lazy("main:funding_detail", kwargs={"pk": self.object.pk})


class ProjectPhaseDeleteView(PermissionRequiredMixin, DeleteView):  # type: ignore [type-arg]
    """Delete view based on a form from the Project Phase model."""

    model = models.ProjectPhase
    template_name = "main/project_phase_delete.html"
    permission_required = "main.delete_project_phase"
    raise_exception = False
    success_url = reverse_lazy("main:projects")


class ProjectPhaseUpdateView(PermissionRequiredMixin, UpdateView):  # type: ignore [type-arg]
    """Update view based on a form from the Project Phase model."""

    model = models.ProjectPhase
    template_name = "main/project_phase_update.html"
    permission_required = "main.change_project_phase"
    raise_exception = False
    form_class = forms.ProjectPhaseForm

    def get_success_url(self):  # type: ignore [no-untyped-def]
        """Django magic function to obtain a dynamic success URL."""
        return reverse_lazy(
            "main:project_phase_detail",
            kwargs={"project_pk": self.object.project.pk, "pk": self.object.pk},
        )
