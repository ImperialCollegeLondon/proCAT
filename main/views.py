"""Views for the main app."""

from typing import Any

import bokeh
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.forms import Form, ModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    FormView,
    TemplateView,
    View,
)
from django_filters.views import FilterView
from django_tables2 import RequestConfig, SingleTableMixin

from . import forms, models, plots, report, tables


def index(request: HttpRequest) -> HttpResponse:
    """View for the index page, using the home template."""
    return render(request, "main/home.html")


class RegistrationView(CreateView):  # type: ignore [type-arg]
    """View to register new users.

    TODO: This is a placeholder for development. When SSO is implemented, this won't be
    needed since available users will be retrieved automatically.
    """

    form_class = forms.CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"


class ProjectsListView(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """View to display the list of projects split in five pre-filtered tables."""

    model = models.Project
    template_name = "main/projects.html"
    filterset_fields = ("nature", "department", "status", "charging")
    permission_required = "main.view_project"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add multiple pre-filtered tables to the context."""
        context = super().get_context_data(**kwargs)

        base_qs = self.get_queryset()

        buckets = [
            ("Active", {"status": "Active"}, "active-"),
            ("Maintenance", {"status": "Maintenance"}, "maintenance-"),
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


class CapacityPlanningView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View that renders the Capacity Planning page."""

    template_name = "main/capacity_planning.html"
    permission_required = "main.view_project"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore
        """Add HTML components and Bokeh version to the context."""
        context = super().get_context_data(**kwargs)
        layout = plots.create_capacity_planning_layout()
        context.update(plots.html_components_from_plot(layout))
        context["bokeh_version"] = bokeh.__version__
        return context


class CostRecoveryView(LoginRequiredMixin, PermissionRequiredMixin, FormView):  # type: ignore [type-arg]
    """View that renders the Cost Recovery page."""

    template_name = "main/cost_recovery.html"
    permission_required = "main.view_project"
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


class ProjectCreateInlineView(PermissionRequiredMixin, View):
    """Create a Project together with its Funding and Phases in one page.

    This view lets a new project be created with its funding and phases all
    filled in together on a single page, via the `FundingInlineFormSet` and
    `ProjectPhaseInlineFormSet` formsets, rather than requiring the project
    to be created first and its funding/phases added separately afterwards.
    """

    permission_required = (
        "main.create_project",
        "main.create_funding",
        "main.create_project_phase",
    )
    raise_exception = False
    template_name = "main/project_inline_form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render an empty Project form with empty Funding/Phase formsets."""
        context = {
            "project_form": forms.ProjectForm(),
            "funding_formset": forms.FundingInlineFormSet(prefix="funding"),
            "phase_formset": forms.ProjectPhaseInlineFormSet(prefix="phase"),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Validate and save the Project, then its Funding and Phase rows.

        The project is saved first, so that the funding and phase rows (which
        reference it via a foreign key) can be validated and saved against a
        real primary key. Everything happens inside one atomic transaction:
        if the funding or phase formsets turn out to be invalid, the project
        creation is rolled back too, and the whole page is redisplayed with
        every error shown together.
        """
        project_form = forms.ProjectForm(request.POST)

        if not project_form.is_valid():
            context = {
                "project_form": project_form,
                "funding_formset": forms.FundingInlineFormSet(
                    request.POST, prefix="funding"
                ),
                "phase_formset": forms.ProjectPhaseInlineFormSet(
                    request.POST, prefix="phase"
                ),
            }
            return render(request, self.template_name, context)

        with transaction.atomic():
            project = project_form.save()
            funding_formset = forms.FundingInlineFormSet(
                request.POST, instance=project, prefix="funding"
            )
            phase_formset = forms.ProjectPhaseInlineFormSet(
                request.POST, instance=project, prefix="phase"
            )
            # Evaluate both explicitly (rather than `and`-chaining) so that,
            # if one of them is invalid, the other's errors are still
            # available to show alongside it.
            funding_valid = funding_formset.is_valid()
            phase_valid = phase_formset.is_valid()

            if funding_valid and phase_valid:
                funding_formset.save()
                phase_formset.save()
                return redirect("main:project_detail", pk=project.pk)

            transaction.set_rollback(True)

        return render(
            request,
            self.template_name,
            {
                "project_form": project_form,
                "funding_formset": funding_formset,
                "phase_formset": phase_formset,
            },
        )


class ProjectUpdateInlineView(PermissionRequiredMixin, View):
    """Update a Project together with its Funding and Phases in one page."""

    permission_required = (
        "main.change_project",
        "main.change_funding",
        "main.change_project_phase",
    )
    raise_exception = False
    template_name = "main/project_inline_form.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Render the Project form with its Funding/Phase formsets pre-filled."""
        project = get_object_or_404(models.Project, pk=pk)
        context = {
            "project": project,
            "project_form": forms.ProjectForm(instance=project),
            "funding_formset": forms.FundingInlineFormSet(
                instance=project, prefix="funding"
            ),
            "phase_formset": forms.ProjectPhaseInlineFormSet(
                instance=project, prefix="phase"
            ),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Validate and save the Project together with its Funding/Phase rows.

        Unlike the create view, the project already has a primary key, so all
        three forms/formsets can be validated together up front.
        """
        project = get_object_or_404(models.Project, pk=pk)
        project_form = forms.ProjectForm(request.POST, instance=project)
        funding_formset = forms.FundingInlineFormSet(
            request.POST, instance=project, prefix="funding"
        )
        phase_formset = forms.ProjectPhaseInlineFormSet(
            request.POST, instance=project, prefix="phase"
        )

        # Evaluate all three explicitly so every error can be shown together.
        project_valid = project_form.is_valid()
        funding_valid = funding_formset.is_valid()
        phase_valid = phase_formset.is_valid()

        if project_valid and funding_valid and phase_valid:
            with transaction.atomic():
                project = project_form.save()
                funding_formset.save()
                phase_formset.save()
            return redirect("main:project_detail", pk=project.pk)

        return render(
            request,
            self.template_name,
            {
                "project": project,
                "project_form": project_form,
                "funding_formset": funding_formset,
                "phase_formset": phase_formset,
            },
        )


class ProjectDetailInlineView(PermissionRequiredMixin, View):
    """Display a Project together with its Funding and Phases in one page.

    This is the read-only counterpart of `ProjectCreateInlineView` and
    `ProjectUpdateInlineView`: it shows the same Project/Funding/Phases
    layout, but with every field disabled and without any of the
    add-row/save affordances, since nothing here can be edited.
    """

    permission_required = (
        "main.view_project",
        "main.view_funding",
        "main.view_project_phase",
    )
    raise_exception = False
    template_name = "main/project_inline_detail.html"

    @staticmethod
    def _disable(form: ModelForm) -> ModelForm:  # type: ignore [type-arg]
        """Mark every field widget of a form as disabled/read-only.

        Args:
            form: The form whose fields should be disabled.

        Return:
            The same form, with all its field widgets disabled.
        """
        for field in form.fields.keys():
            form.fields[field].widget.attrs["disabled"] = True
            form.fields[field].widget.attrs["readonly"] = True
        return form

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Render the Project, Funding and Phase details, all read-only.

        Unlike the create/update views, no formsets are used here: each
        existing Funding/Phase row is rendered as its own disabled
        `ModelForm`, since there is no need for the extra blank rows,
        management form, or delete checkboxes that a formset would add.
        """
        project = get_object_or_404(models.Project, pk=pk)

        context = {
            "project": project,
            "project_form": self._disable(forms.ProjectForm(instance=project)),
            "funding_header_form": forms.FundingInlineForm(),
            "funding_forms": [
                self._disable(forms.FundingInlineForm(instance=funding))
                for funding in project.funding_source.all()
            ],
            "phase_header_form": forms.ProjectPhaseInlineForm(),
            "phase_forms": [
                self._disable(forms.ProjectPhaseInlineForm(instance=phase))
                for phase in project.phases.all()
            ],
        }
        return render(request, self.template_name, context)
