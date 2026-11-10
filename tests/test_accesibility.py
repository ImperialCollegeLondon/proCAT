"""Implement accessibility tests."""

from pprint import pformat

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from playwright.sync_api import Page
from pytest_playwright_axe import Axe


@pytest.fixture
def login(live_server, context):
    """Return a helper that logs a given user into the browser context — no UI."""

    def _login(user):
        client = Client()
        client.force_login(user)  # creates the session server-side
        cookie = client.cookies[settings.SESSION_COOKIE_NAME]
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": cookie.value,
                    "url": live_server.url,
                }
            ]
        )

    return _login


def check_accessibility(page: Page, filename: str) -> None:
    """Check the accessibility of the page at the given url.

    Args:
        page: The page whose accessibility is to be checked.
        filename: The filename (ex. extension) to be used in the reports.

    Raises:
        ValueError: if any accessibility violation is found.
    """
    violations = Axe().run(
        page,
        filename=filename,
        report_on_violation_only=True,
        json_report_generated=False,
    )["violations"]
    if violations:
        raise ValueError(f"Accessibility violations found:\n{pformat(violations)}")


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("project_mid")
@pytest.mark.xfail(reason="Accessibility violations found.")
def test_homepage(live_server, page: Page):
    """Test accessibility in the public home page."""
    page_url = "main:home"
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url.split(":")[-1])


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("project_mid")
@pytest.mark.parametrize(
    "page_url",
    [
        pytest.param("main:projects"),
        pytest.param("main:capacity_planning"),
        pytest.param("main:cost_recovery"),
    ],
)
@pytest.mark.xfail(reason="Accessibility violations found.")
def test_team_pages(live_server, page: Page, login, user, page_url):
    """Test accessibility in selected pages."""
    login(user)
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url.split(":")[-1])


@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(reason="Accessibility violations found.")
def test_project_detail_page(live_server, page: Page, login, user, project_mid):
    """Test accessibility in selected pages."""
    page_url = "main:project_detail"
    login(user)
    url = live_server.url + reverse(page_url, kwargs={"pk": project_mid.pk})
    page.goto(url)
    check_accessibility(page, page_url.split(":")[-1])


@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(reason="Accessibility violations found.")
def test_create_project_page(live_server, page: Page, login, admin_user):
    """Test accessibility in selected pages."""
    page_url = "main:project_create"
    login(admin_user)
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url.split(":")[-1])


@pytest.mark.django_db(transaction=True)
@pytest.mark.xfail(reason="Accessibility violations found.")
def test_project_update_page(live_server, page: Page, login, admin_user, project_mid):
    """Test accessibility in selected pages."""
    page_url = "main:project_update"
    login(admin_user)
    url = live_server.url + reverse(page_url, kwargs={"pk": project_mid.pk})
    page.goto(url)
    check_accessibility(page, page_url.split(":")[-1])
