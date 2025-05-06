"""Views for the main app."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """View that renders the index page."""
    return render(request=request, template_name="main/index.html")
