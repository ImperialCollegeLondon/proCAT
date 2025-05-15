"""Urls module for the main app."""

from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.RegistrationView.as_view(), name="auth_register"),
    path("projects/", views.ProjectsListView.as_view(), name="projects"),
]
