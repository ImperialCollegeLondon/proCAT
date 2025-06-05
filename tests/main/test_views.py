"""Test suite for the main views.

This test module includes tests for main views of the app ensuring that:
  - The correct templates are used.
  - The correct status codes are returned.
"""

from http import HTTPStatus

import pytest
from django.urls import reverse

from .view_utils import LoginRequiredMixin, TemplateOkMixin


class TestIndex(TemplateOkMixin):
    """Test suite for the index view."""

    _template_name = "main/index.html"

    def _get_url(self):
        return reverse("main:index")


class TestProjectsListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the projects view."""

    _template_name = "main/projects.html"

    def _get_url(self):
        return reverse("main:projects")


class TestFundingListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the funding view."""

    _template_name = "main/funding.html"

    def _get_url(self):
        return reverse("main:funding")


class TestCapacitiesListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the capacities view."""

    _template_name = "main/capacities.html"

    def _get_url(self):
        return reverse("main:capacities")


@pytest.mark.usefixtures("project")
class TestProjectsDetailView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the projects view."""

    _template_name = "main/project_detail.html"

    def _get_url(self):
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        return reverse("main:project_detail", kwargs={"pk": project.pk})

    def test_get(self, auth_client, project):
        """Tests the get method and the data provided."""
        from main import tables

        endpoint = reverse("main:project_detail", kwargs={"pk": project.pk})

        response = auth_client.get(endpoint)
        assert response.status_code == HTTPStatus.OK
        assert "form" in response.context
        assert response.context["project_name"] == project.name
        assert isinstance(response.context["funding_table"], tables.FundingTable)

        # The form should be readonly
        form = response.context["form"]
        for field in form.fields.keys():
            assert form.fields[field].widget.attrs["disabled"]
            assert form.fields[field].widget.attrs["readonly"]


@pytest.mark.usefixtures("funding")
class TestFundingDetailView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the funding view."""

    _template_name = "main/funding_detail.html"

    def _get_url(self):
        from main import models

        funding = models.Funding.objects.get(project_code="1234")

        return reverse("main:funding_detail", kwargs={"pk": funding.pk})

    def test_get(self, auth_client, funding):
        """Tests the get method and the data provided."""
        endpoint = reverse("main:funding_detail", kwargs={"pk": funding.pk})

        response = auth_client.get(endpoint)
        assert response.status_code == HTTPStatus.OK
        assert "form" in response.context
        assert response.context["funding_name"] == str(funding)

        # The form should be readonly
        form = response.context["form"]
        for field in form.fields.keys():
            assert form.fields[field].widget.attrs["disabled"]
            assert form.fields[field].widget.attrs["readonly"]
