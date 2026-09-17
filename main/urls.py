"""Urls module for the main app."""

from django.conf import settings
from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="home"),
    path("projects/", views.ProjectsListView.as_view(), name="projects"),
    path("capacities/", views.CapacitiesListView.as_view(), name="capacities"),
    path(
        "projects/create/",
        views.ProjectCreateInlineView.as_view(),
        name="project_create",
    ),
    path(
        "projects/<slug:pk>/",
        views.ProjectDetailInlineView.as_view(),
        name="project_detail",
    ),
    path(
        "projects/<slug:pk>/update",
        views.ProjectUpdateInlineView.as_view(),
        name="project_update",
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

if not settings.USE_OIDC:
    urlpatterns += [
        path("register/", views.RegistrationView.as_view(), name="auth_register"),
    ]
