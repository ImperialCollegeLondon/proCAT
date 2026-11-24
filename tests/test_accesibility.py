"""Implement accessibility tests."""

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from playwright.sync_api import Page
from pytest_playwright_axe import Axe

# Axe rules each page is currently known to fail. Remove a rule from here once it is
# fixed.
KNOWN_FAILURES: dict[str, set[str]] = {
    "main:home": {
        "color-contrast",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    "main:projects": {
        "color-contrast",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    # The Bokeh plots will keep failing `region` even after the main landmark is
    # added. Fixing that has been deferred.
    "main:capacity_planning": {
        "color-contrast",
        "heading-order",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    # As above, the Bokeh plots will keep failing `region`.
    "main:cost_recovery": {
        "color-contrast",
        "heading-order",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    "main:project_detail": {
        "color-contrast",
        "heading-order",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    "main:project_create": {
        "color-contrast",
        "heading-order",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
    "main:project_update": {
        "color-contrast",
        "heading-order",
        "landmark-one-main",
        "link-name",
        "page-has-heading-one",
        "region",
    },
}


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


def compare_violations(
    violations: list[dict], known: set[str], page_url: str
) -> str | None:
    """Compare the violations reported by axe against the known failures.

    Args:
        violations: The list of violations, as reported by axe.
        known: The IDs of the rules the page is known to fail.
        page_url: The name of the page, used in the error message.

    Returns:
        None if the violations match the known failures exactly. Otherwise, a message
        describing the unexpected failures and the known failures that now pass.
    """
    reported = {violation["id"] for violation in violations}
    lines = [
        f"{rule} fails on {page_url} and is not in KNOWN_FAILURES."
        for rule in sorted(reported - known)
    ]
    lines += [
        f"{rule} now passes on {page_url}; remove it from KNOWN_FAILURES."
        for rule in sorted(known - reported)
    ]
    if lines:
        lines.append("See the reports in axe-reports/ for details.")
    return "\n".join(lines) or None


def check_accessibility(page: Page, page_url: str) -> None:
    """Check the accessibility of the page against its known failures.

    Args:
        page: The page whose accessibility is to be checked.
        page_url: The name of the page (ex. "main:home"). It is used to find the known
            failures and, after the colon, as the filename of the reports.

    Raises:
        AssertionError: if axe reports a failure that is not in the known failures, or
            if a known failure is no longer reported.
    """
    violations = Axe().run(
        page,
        filename=page_url.split(":")[-1],
        report_on_violation_only=True,
        json_report_generated=False,
    )["violations"]
    message = compare_violations(violations, KNOWN_FAILURES[page_url], page_url)
    assert message is None, f"\n{message}"


# Tests for the compare violations helper function
def test_compare_violations_new_failure():
    """An unexpected rule is reported with its ID and the page."""
    violations = [{"id": "color-contrast"}, {"id": "link-name"}]
    message = compare_violations(violations, {"color-contrast"}, "main:home")

    assert message is not None

    # This one is new
    assert "link-name fails on main:home" in message

    # This one is the old one, and still fails, so it is not reported
    assert "color-contrast" not in message


def test_compare_violations_fixed_failure():
    """A known rule that no longer fails asks to be removed from the list."""
    violations = [{"id": "color-contrast"}]
    message = compare_violations(
        violations, {"color-contrast", "link-name"}, "main:home"
    )

    assert message is not None

    # This one is now passing, so it needs to be removed
    assert "link-name now passes on main:home" in message
    assert "remove it from KNOWN_FAILURES" in message

    # This one is the old one, and still fails, so it is not reported
    assert "color-contrast" not in message


def test_compare_violations_exact_match():
    """No message is returned when violations match the known failures."""
    violations = [{"id": "color-contrast"}, {"id": "region"}]

    # All the violations are the known ones, so nothing is reported
    assert compare_violations(violations, {"color-contrast", "region"}, "x") is None
    assert compare_violations([], set(), "x") is None


# Tests for the main pages
@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("project_mid")
def test_homepage(live_server, page: Page):
    """Test accessibility in the public home page."""
    page_url = "main:home"
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url)


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
def test_team_pages(live_server, page: Page, login, user, page_url):
    """Test accessibility in project list, capacity planning and cost recovery pages."""
    login(user)
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url)


@pytest.mark.django_db(transaction=True)
def test_project_detail_page(live_server, page: Page, login, user, project_mid):
    """Test accessibility in the project detail page."""
    page_url = "main:project_detail"
    login(user)
    url = live_server.url + reverse(page_url, kwargs={"pk": project_mid.pk})
    page.goto(url)
    check_accessibility(page, page_url)


@pytest.mark.django_db(transaction=True)
def test_create_project_page(live_server, page: Page, login, admin_user):
    """Test accessibility in the create project page."""
    page_url = "main:project_create"
    login(admin_user)
    url = live_server.url + reverse(page_url)
    page.goto(url)
    check_accessibility(page, page_url)


@pytest.mark.django_db(transaction=True)
def test_project_update_page(live_server, page: Page, login, admin_user, project_mid):
    """Test accessibility in the update project page."""
    page_url = "main:project_update"
    login(admin_user)
    url = live_server.url + reverse(page_url, kwargs={"pk": project_mid.pk})
    page.goto(url)
    check_accessibility(page, page_url)
