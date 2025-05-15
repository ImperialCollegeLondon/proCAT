"""Views for the main app."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django_tables2 import SingleTableView

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


class ProjectsListView(LoginRequiredMixin, SingleTableView):
    """View to display the list of projects."""

    model = models.Project
    table_class = tables.ProjectTable
    template_name = "main/projects.html"
