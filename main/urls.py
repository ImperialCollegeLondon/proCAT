"""Urls module for the main app."""

from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.RegistrationView.as_view(), name="auth_register"),
    path("projects/", views.ProjectsListView.as_view(), name="projects"),
    path("funding/", views.FundingListView.as_view(), name="funding"),
    path("capacities/", views.CapacitiesListView.as_view(), name="capacities"),
    path(
        "projects/<slug:pk>/", views.ProjectDetailView.as_view(), name="project_detail"
    ),
    path(
        "funding/<slug:pk>/", views.FundingDetailView.as_view(), name="funding_detail"
    ),
]
