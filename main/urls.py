"""Urls module for the main app."""

from django.conf import settings
from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.ProjectsListView.as_view(), name="projects"),
    path("funding/", views.FundingListView.as_view(), name="funding"),
    path("capacities/", views.CapacitiesListView.as_view(), name="capacities"),
    path(
        "funding/create/",
        views.FundingCreateView.as_view(),
        name="funding_create",
    ),
    path(
        "projects/create/",
        views.ProjectCreateView.as_view(),
        name="project_create",
    ),
    path(
        "funding/<slug:pk>/update",
        views.FundingUpdateView.as_view(),
        name="funding_update",
    ),
    path(
        "projects/<slug:pk>/", views.ProjectDetailView.as_view(), name="project_detail"
    ),
    path(
        "projects/<slug:pk>/update",
        views.ProjectUpdateView.as_view(),
        name="project_update",
    ),
    path(
        "projects/<slug:project_pk>/phase/<slug:pk>",
        views.ProjectPhaseDetailView.as_view(),
        name="project_phase_detail",
    ),
    path(
        "project-phase/create/",
        views.ProjectPhaseCreateView.as_view(),
        name="project_phase_create",
    ),
    path(
        "projects/<slug:project_pk>/phase/<slug:pk>/delete/",
        views.ProjectPhaseDeleteView.as_view(),
        name="project_phase_delete",
    ),
    path(
        "funding/<slug:pk>/", views.FundingDetailView.as_view(), name="funding_detail"
    ),
    path(
        "capacity_planning/",
        views.CapacityPlanningView.as_view(),
        name="capacity_planning",
    ),
    path(
        "cost_recovery/",
        views.CostRecoveryView.as_view(),
        name="cost_recovery",
    ),
]

if settings.DEBUG and not settings.USE_OIDC:
    urlpatterns += [
        path("register/", views.RegistrationView.as_view(), name="auth_register"),
    ]
