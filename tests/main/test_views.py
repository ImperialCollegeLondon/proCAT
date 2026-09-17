"""Test suite for the main views.

This test module includes tests for main views of the app ensuring that:
  - The correct templates are used.
  - The correct status codes are returned.
"""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from main.models import Project

from .view_utils import LoginRequiredMixin, PermissionRequiredMixin, TemplateOkMixin


class TestProjectsListView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the projects view."""

    _template_name = "main/projects.html"

    def _get_url(self):
        return reverse("main:projects")

    @pytest.mark.django_db
    def test_not_authorized(self, auth_client_unauthorizeduser):
        """Test that an unauthorized user cannot see the page."""
        endpoint = self._get_url()
        response = auth_client_unauthorizeduser.get(endpoint)

        # Check status code and context
        assert response.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.django_db
    def test_get_context_data(self, auth_client, project):
        """Test that the view returns the correct context data with filtered tables."""
        endpoint = reverse("main:projects")
        response = auth_client.get(endpoint)

        # Check status code and context
        assert response.status_code == HTTPStatus.OK
        assert "tables" in response.context

        # Check that there are 6 tables, one for each status
        tables = response.context["tables"]
        assert len(tables) == 6

        # Check that the tables have the correct titles and prefixes
        expected_tables = [
            ("Active", "active-"),
            ("Maintenance", "maintenance-"),
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
        # Add a check for 'Maintenance'
        Project.objects.create(
            name="Test Maintenance",
            status="Maintenance",
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

        # Check Maintenance table
        maintenance_table = tables["Maintenance"]
        maintenance_projects = [p for p in maintenance_table.data]
        assert len(maintenance_projects) == 1
        assert all(p.status == "Maintenance" for p in maintenance_projects)

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


class TestCapacitiesListView(
    PermissionRequiredMixin, LoginRequiredMixin, TemplateOkMixin
):
    """Test suite for the capacities view."""

    _template_name = "main/capacities.html"

    def _get_url(self):
        return reverse("main:capacities")


class TestProjectCreateInlineView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the Project Create (with Funding/Phase details) view."""

    _template_name = "main/project_inline_form.html"

    def _get_url(self):
        return reverse("main:project_create")

    def test_post_creates_project_funding_and_phase_together(
        self, admin_client, department, user
    ):
        """A single POST creates the Project, its Funding and its Phase rows."""
        data = {
            "name": "Inline Project",
            "nature": "Support",
            "pi": "John Smith",
            "department": department.pk,
            "lead": user.pk,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "status": "Tentative",
            "charging": "Actual",
            "funding-TOTAL_FORMS": "1",
            "funding-INITIAL_FORMS": "0",
            "funding-MIN_NUM_FORMS": "0",
            "funding-MAX_NUM_FORMS": "1000",
            "funding-0-source": "Internal",
            "funding-0-budget": "1000",
            "funding-0-daily_rate": "389",
            "phase-TOTAL_FORMS": "1",
            "phase-INITIAL_FORMS": "0",
            "phase-MIN_NUM_FORMS": "0",
            "phase-MAX_NUM_FORMS": "1000",
            "phase-0-days": "100",
            "phase-0-start_date": "2025-01-01",
            "phase-0-end_date": "2025-12-31",
        }

        response = admin_client.post(self._get_url(), data)

        # Check we got a redirect URL (not a re-render with errors)
        assert response.status_code == HTTPStatus.FOUND

        project = Project.objects.get(name="Inline Project")
        assert project.funding_source.count() == 1
        assert project.phases.count() == 1

    def test_post_with_invalid_phase_rolls_back_everything(
        self, admin_client, department, user
    ):
        """If the phase formset is invalid, nothing should be persisted at all."""
        data = {
            "name": "Should Not Be Created",
            "nature": "Support",
            "pi": "John Smith",
            "department": department.pk,
            "lead": user.pk,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "status": "Tentative",
            "charging": "Actual",
            "funding-TOTAL_FORMS": "0",
            "funding-INITIAL_FORMS": "0",
            "funding-MIN_NUM_FORMS": "0",
            "funding-MAX_NUM_FORMS": "1000",
            "phase-TOTAL_FORMS": "1",
            "phase-INITIAL_FORMS": "0",
            "phase-MIN_NUM_FORMS": "0",
            "phase-MAX_NUM_FORMS": "1000",
            # Outside the project's own start/end dates: rejected per-row.
            "phase-0-days": "10",
            "phase-0-start_date": "2020-01-01",
            "phase-0-end_date": "2020-01-31",
        }

        response = admin_client.post(self._get_url(), data)

        # Invalid formset: the page is re-rendered with errors, not a redirect.
        assert response.status_code == HTTPStatus.OK
        assert not Project.objects.filter(name="Should Not Be Created").exists()

    def test_post_active_without_funding_rejected(self, admin_client, department, user):
        """Creating a project directly as 'Active' (no funding) must not be possible."""
        data = {
            "name": "Should Fail",
            "nature": "Support",
            "pi": "John Smith",
            "department": department.pk,
            "lead": user.pk,
            "start_date": timezone.now().date(),
            "end_date": timezone.now().date() + timedelta(days=42),
            "status": "Active",
            "charging": "Actual",
            "funding-TOTAL_FORMS": "0",
            "funding-INITIAL_FORMS": "0",
            "funding-MIN_NUM_FORMS": "0",
            "funding-MAX_NUM_FORMS": "1000",
            "phase-TOTAL_FORMS": "0",
            "phase-INITIAL_FORMS": "0",
            "phase-MIN_NUM_FORMS": "0",
            "phase-MAX_NUM_FORMS": "1000",
        }

        response = admin_client.post(self._get_url(), data)

        # Form is invalid: the page is re-rendered with errors, not a redirect.
        assert response.status_code == HTTPStatus.OK
        assert not Project.objects.filter(name="Should Fail").exists()
        # Check that the expected error is shown to the user
        assert b"Projects cannot be created directly in" in response.content


@pytest.mark.usefixtures("project_static")
class TestProjectUpdateInlineView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the Project Update (with Funding/Phase details) view."""

    _template_name = "main/project_inline_form.html"

    def _get_url(self):
        from main import models

        project = models.Project.objects.get(name="ProCATv2")

        return reverse("main:project_update", kwargs={"pk": project.pk})

    def test_post_adds_funding_and_phase_to_existing_project(
        self, admin_client, project_static
    ):
        """Editing the project can add new Funding/Phase rows in one go."""
        existing_funding_count = project_static.funding_source.count()

        data = {
            "name": "Renamed ProCATv2",
            "nature": "Support",
            "pi": "Jane Doe",
            "department": project_static.department.pk,
            "lead": project_static.lead.pk,
            "start_date": project_static.start_date,
            "end_date": project_static.end_date,
            "status": project_static.status,
            "charging": project_static.charging,
            "funding-TOTAL_FORMS": "1",
            "funding-INITIAL_FORMS": "0",
            "funding-MIN_NUM_FORMS": "0",
            "funding-MAX_NUM_FORMS": "1000",
            "funding-0-source": "Internal",
            "funding-0-budget": "1000",
            "funding-0-daily_rate": "389",
            "phase-TOTAL_FORMS": "1",
            "phase-INITIAL_FORMS": "0",
            "phase-MIN_NUM_FORMS": "0",
            "phase-MAX_NUM_FORMS": "1000",
            "phase-0-days": "50",
            "phase-0-start_date": "2025-01-01",
            "phase-0-end_date": "2025-06-30",
        }

        response = admin_client.post(self._get_url(), data)

        assert response.status_code == HTTPStatus.FOUND

        project_static.refresh_from_db()
        assert project_static.name == "Renamed ProCATv2"
        assert project_static.funding_source.count() == existing_funding_count + 1
        assert project_static.phases.count() == 1

        # Check the update is reflected on the (new, inline) project detail page
        # and on the main projects view.
        for url in [response.url, reverse("main:projects")]:
            page = admin_client.get(url)
            assert page.status_code == HTTPStatus.OK
            assert "Renamed ProCATv2" in page.content.decode()


@pytest.mark.usefixtures("project_static", "phase")
class TestProjectDetailInlineView(PermissionRequiredMixin, TemplateOkMixin):
    """Test suite for the Project Detail (with Funding/Phase details) view."""

    _template_name = "main/project_inline_detail.html"

    def _get_url(self):
        from main import models

        project = models.Project.objects.get(name="ProCATv2")

        return reverse("main:project_detail", kwargs={"pk": project.pk})

    def test_get_shows_project_funding_and_phase_details(
        self, admin_client, project_static, phase
    ):
        """The page shows the Project's existing Funding and Phase rows."""
        response = admin_client.get(self._get_url())

        assert response.status_code == HTTPStatus.OK

        content = response.content.decode()
        assert project_static.name in content

        funding = project_static.funding_source.first()
        assert funding is not None
        assert str(funding.budget) in content

        project_phase = project_static.phases.first()
        assert project_phase is not None
        assert str(project_phase.start_date) in content

        # The forms in context should all be disabled/read-only.
        project_form = response.context["project_form"]
        for field in project_form.fields.keys():
            assert project_form.fields[field].widget.attrs["disabled"]
            assert project_form.fields[field].widget.attrs["readonly"]

        for form in [
            *response.context["funding_forms"],
            *response.context["phase_forms"],
        ]:
            for field in form.fields.keys():
                assert form.fields[field].widget.attrs["disabled"]
                assert form.fields[field].widget.attrs["readonly"]

    def test_get_with_no_funding_or_phases(self, admin_client, project_static):
        """The page renders gracefully when there is no Funding/Phase yet."""
        from main import models

        # Remove the funding/phases created by the project_static/phase fixtures.
        models.Funding.objects.filter(project=project_static).delete()
        models.ProjectPhase.objects.filter(project=project_static).delete()

        response = admin_client.get(self._get_url())

        assert response.status_code == HTTPStatus.OK
        assert response.context["funding_forms"] == []
        assert response.context["phase_forms"] == []


class TestCapacityPlanningView(LoginRequiredMixin, TemplateOkMixin):
    """Test suite for the Capacity Planning view."""

    _template_name = "main/capacity_planning.html"

    def _get_url(self):
        return reverse("main:capacity_planning")

    @pytest.mark.django_db
    def test_not_authorized(self, auth_client_unauthorizeduser):
        """Test that an unauthorized user cannot see the page."""
        endpoint = self._get_url()
        response = auth_client_unauthorizeduser.get(endpoint)

        # Check status code and context
        assert response.status_code == HTTPStatus.FORBIDDEN

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

    @pytest.mark.django_db
    def test_not_authorized(self, auth_client_unauthorizeduser):
        """Test that an unauthorized user cannot see the page."""
        endpoint = self._get_url()
        response = auth_client_unauthorizeduser.get(endpoint)

        # Check status code and context
        assert response.status_code == HTTPStatus.FORBIDDEN

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
