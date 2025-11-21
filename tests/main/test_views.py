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

from .view_utils import LoginRequiredMixin, PermissionRequiredMixin, TemplateOkMixin


class TestProjectsListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the projects view."""

    _template_name = "main/projects.html"

    def _get_url(self):
        return reverse("main:projects")

    @pytest.mark.django_db
    def test_get_context_data(self, auth_client, project):
        """Test that the view returns the correct context data with filtered tables."""
        endpoint = reverse("main:projects")
        response = auth_client.get(endpoint)

        # Check status code and context
        assert response.status_code == HTTPStatus.OK
        assert "tables" in response.context

        # Check that there are 5 tables, one for each status
        tables = response.context["tables"]
        assert len(tables) == 5

        # Check that the tables have the correct titles and prefixes
        expected_tables = [
            ("Active", "active-"),
            ("Confirmed", "confirmed-"),
            ("Tentative", "tentative-"),
            ("Finished", "finished-"),
            ("Not done", "not-done-"),
        ]

        for i, (title, prefix) in enumerate(expected_tables):
            assert tables[i][0] == title
            assert tables[i][1].prefix == prefix

    @pytest.mark.django_db
    def test_filtered_tables(self, auth_client, user, department, project):
        """Test that each table contains only projects with the matching status."""
        # Create projects with different statuses using the existing user fixture
        Project.objects.create(
            name="Test Active",
            status="Active",
            department=department,
            lead=user,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        Project.objects.create(
            name="Test Confirmed",
            status="Confirmed",
            department=department,
            lead=user,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        Project.objects.create(
            name="Test Tentative",
            status="Tentative",
            department=department,
            lead=user,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        Project.objects.create(
            name="Test Finished",
            status="Finished",
            department=department,
            lead=user,
            start_date=project.start_date,
            end_date=project.end_date,
        )
        Project.objects.create(
            name="Test Not done",
            status="Not done",
            department=department,
            lead=user,
            start_date=project.start_date,
            end_date=project.end_date,
        )

        endpoint = reverse("main:projects")
        response = auth_client.get(endpoint)

        # Check each table contains only projects with the correct status
        tables = dict(response.context["tables"])

        # Check Active table
        active_table = tables["Active"]
        active_projects = [p for p in active_table.data]
        assert len(active_projects) >= 1  # Could include default project from fixture
        assert all(p.status == "Active" for p in active_projects)

        # Check Confirmed table
        confirmed_table = tables["Confirmed"]
        confirmed_projects = [p for p in confirmed_table.data]
        assert len(confirmed_projects) == 1
        assert all(p.status == "Confirmed" for p in confirmed_projects)

        # Check Tentative table
        tentative_table = tables["Tentative"]
        tentative_projects = [p for p in tentative_table.data]
        assert len(tentative_projects) == 1
        assert all(p.status == "Tentative" for p in tentative_projects)

        # Check Finished table
        finished_table = tables["Finished"]
        finished_projects = [p for p in finished_table.data]
        assert len(finished_projects) == 1
        assert all(p.status == "Finished" for p in finished_projects)

        # Check Not done table
        not_done_table = tables["Not done"]
        not_done_projects = [p for p in not_done_table.data]
        assert len(not_done_projects) == 1
        assert all(p.status == "Not done" for p in not_done_projects)

    @pytest.mark.django_db
    def test_order_weeks_to_deadline(self, auth_client):
        """Test the order_weeks_to_deadline method (prefixed param)."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "weeks_to_deadline"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "weeks_to_deadline"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "-weeks_to_deadline"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "weeks_to_deadline"
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_total_effort(self, auth_client):
        """Test the order_total_effort method (prefixed param)."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "total_effort"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "total_effort"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "-total_effort"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "total_effort"
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_days_left(self, auth_client):
        """Test the order_days_left method (prefixed param)."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "days_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "days_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "-days_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "days_left"
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_total_funding_left(self, auth_client):
        """Test the total_funding_left method (prefixed param)."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:projects")
            order_mock.return_value = Project.objects.all()

            # Test ascending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "total_funding_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "total_funding_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            order_mock.reset_mock()
            auth_client.get(endpoint, {"active-sort": "-total_funding_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "total_funding_left"
            assert order_mock.call_args.args[2]


class TestFundingListView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the funding view."""

    _template_name = "main/funding.html"

    def _get_url(self):
        return reverse("main:funding")

    @pytest.mark.django_db
    def test_order_effort(self, admin_client):
        """Test the order_effort method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:funding")
            order_mock.return_value = Funding.objects.all()

            # Test ascending sort
            admin_client.get(endpoint, {"sort": "effort"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "effort"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            admin_client.get(endpoint, {"sort": "-effort"})
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_effort_left(self, admin_client):
        """Test the order_effort_left method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:funding")
            order_mock.return_value = Funding.objects.all()

            # Test ascending sort
            admin_client.get(endpoint, {"sort": "effort_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "effort_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            admin_client.get(endpoint, {"sort": "-effort_left"})
            assert order_mock.call_args.args[2]

    @pytest.mark.django_db
    def test_order_funding_left(self, admin_client):
        """Test the order_funding_left method."""
        with patch("main.tables.order_queryset_by_property") as order_mock:
            endpoint = reverse("main:funding")
            order_mock.return_value = Funding.objects.all()

            # Test ascending sort
            admin_client.get(endpoint, {"sort": "funding_left"})
            order_mock.assert_called()
            assert order_mock.call_args.args[1] == "funding_left"
            assert not order_mock.call_args.args[2]

            # Test descending sort
            admin_client.get(endpoint, {"sort": "-funding_left"})
            assert order_mock.call_args.args[2]


class TestCapacitiesListView(
    PermissionRequiredMixin, LoginRequiredMixin, TemplateOkMixin
):
    """Test suite for the capacities view."""

    _template_name = "main/capacities.html"

    def _get_url(self):
        return reverse("main:capacities")


@pytest.mark.usefixtures("project")
class TestProjectsDetailView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the projects view."""

    _template_name = "main/project_detail.html"

    def _get_url(self):
        from main import models

        project = models.Project.objects.get(name="ProCAT")

        return reverse("main:project_detail", kwargs={"pk": project.pk})

    def test_get(self, admin_client, project):
        """Tests the get method and the data provided."""
        from main import tables

        endpoint = reverse("main:project_detail", kwargs={"pk": project.pk})

        response = admin_client.get(endpoint)
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
class TestFundingDetailView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the funding view."""

    _template_name = "main/funding_detail.html"

    def _get_url(self):
        from main import models

        funding = models.Funding.objects.get(activity="G12345")

        return reverse("main:funding_detail", kwargs={"pk": funding.pk})

    def test_get(self, admin_client, funding):
        """Tests the get method and the data provided."""
        from main import tables

        endpoint = reverse("main:funding_detail", kwargs={"pk": funding.pk})

        response = admin_client.get(endpoint)
        assert response.status_code == HTTPStatus.OK
        assert "form" in response.context
        assert response.context["funding_name"] == str(funding)

        assert "monthly_charges_table" in response.context
        assert isinstance(
            response.context["monthly_charges_table"], tables.MonthlyChargeTable
        )

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
        assert "<script" in response.context["script"]
        assert "<div" in response.context["div"]
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


@pytest.mark.django_db()
class TestProjectCreateView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the Project Create view."""

    _template_name = "main/project_form.html"

    def _get_url(self):
        return reverse("main:project_create")

    def test_post(self, admin_client, project_create_post):
        """Tests the post method to update the model and ."""
        post = admin_client.post("/projects/create/", project_create_post)

        # Check we got redirect URL (not a refresh 200)
        assert post.status_code == HTTPStatus.FOUND
        # Check submission made it to DB
        new_object = Project.objects.get(name="Project 123")
        assert new_object.pi == "John Smith"

        # Check submission rendered in projects view
        response = admin_client.get(reverse("main:projects"))
        assert response.status_code == HTTPStatus.OK
        projects = response.context["project_list"].values("name")[0]
        assert "Project 123" in projects["name"]
