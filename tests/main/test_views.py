"""Test suite for the main views.

This test module includes tests for main views of the app ensuring that:
  - The correct templates are used.
  - The correct status codes are returned.
"""

from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.urls import reverse

from main.models import Funding, Project

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

    @pytest.mark.django_db
    def test_order_weeks_to_deadline(self, auth_client):
        """Test the order_weeks_to_deadline method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            auth_client.get(endpoint, {"sort": "weeks_to_deadline"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "weeks_to_deadline"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            auth_client.get(endpoint, {"sort": "-weeks_to_deadline"})
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_total_effort(self, auth_client):
        """Test the order_total_effort method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            auth_client.get(endpoint, {"sort": "total_effort"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "total_effort"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            auth_client.get(endpoint, {"sort": "-total_effort"})
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_days_left(self, auth_client):
        """Test the order_days_left method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            auth_client.get(endpoint, {"sort": "days_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "days_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            auth_client.get(endpoint, {"sort": "-days_left"})
            assert order_mock.call_args.args[2]


class TestFundingListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the funding view."""

    _template_name = "main/funding.html"

    def _get_url(self):
        return reverse("main:funding")

    @pytest.mark.django_db
    def test_order_effort(self, auth_client):
        """Test the order_effort method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:funding")
            order_mock.return_value = Funding.objects.all()

            # Test ascending sort
            auth_client.get(endpoint, {"sort": "effort"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "effort"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            auth_client.get(endpoint, {"sort": "-effort"})
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_effort_left(self, auth_client):
        """Test the order_effort_left method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:funding")
            order_mock.return_value = Funding.objects.all()

            # Test ascending sort
            auth_client.get(endpoint, {"sort": "effort_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "effort_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            auth_client.get(endpoint, {"sort": "-effort_left"})
            assert order_mock.call_args.args[2]


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

        funding = models.Funding.objects.get(activity="G12345")

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


class TestCapacityPlanningView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the Capacity Planning view."""

    _template_name = "main/capacity_planning.html"

    def _get_url(self):
        return reverse("main:capacity_planning")

    def test_get(self, auth_client, funding):
        """Tests the get method and the data provided."""
        import bokeh

        endpoint = reverse("main:capacity_planning")
        response = auth_client.get(endpoint)
        assert response.status_code == HTTPStatus.OK
        assert "<script" in response.context["script"]
        assert "<div" in response.context["div"]
        assert response.context["bokeh_version"] == bokeh.__version__


class TestCostRecoveryView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the Cost Recovery view."""

    _template_name = "main/cost_recovery.html"

    def _get_url(self):
        return reverse("main:cost_recovery")

    def test_get(self, auth_client):
        """Tests the get method and the data provided."""
        import bokeh

        endpoint = reverse("main:cost_recovery")
        response = auth_client.get(endpoint)
        assert response.status_code == HTTPStatus.OK
        assert "<script" in response.context["timeseries_script"]
        assert "<div" in response.context["timeseries_div"]
        assert "<script" in response.context["bar_script"]
        assert "<div" in response.context["bar_div"]
        assert response.context["bokeh_version"] == bokeh.__version__

    def test_form_valid(self, user):
        """Tests the form_valid method.

        Tests that when the form is submitted, a CSV file is generated for download.
        """
        from main import views

        rf = RequestFactory()
        year, month = 2025, 7
        request = rf.post(
            "main:cost_recovery",
            {
                "year": year,
                "month": month,
            },
        )
        request.user = user
        response = views.CostRecoveryView.as_view()(request)
        assert response.headers["Content-Type"] == "text/csv"
        assert f"charges_report_{month}-{year}.csv" in response["Content-Disposition"]
