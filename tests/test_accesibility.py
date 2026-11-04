"""Implement accessibility tests."""

from pprint import pformat

import pytest
from django.urls import reverse
from playwright.sync_api import Page
from pytest_playwright_axe import Axe


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "page_url",
    [
        pytest.param("main:home"),
        pytest.param("main:projects"),
        pytest.param("main:capacity_planning"),
        pytest.param("main:cost_recovery"),
        pytest.param("main:project_create"),
    ],
)
def test_homepage(live_server, page: Page, page_url):
    """Test accessibility in selected pages."""
    page.goto(live_server.url + reverse(page_url))
    violations = Axe().run(page, report_on_violation_only=True)["violations"]
    if violations:
        raise ValueError(f"Accessibility violations found:\n{pformat(violations)}")
