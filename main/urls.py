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
        "projects/<slug:pk>/", views.ProjectDetailView.as_view(), name="project_detail"
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

if settings.DEBUG:
    urlpatterns += [
        path("register/", views.RegistrationView.as_view(), name="auth_register"),
    ]
