"""Utility module for view tests."""

from http import HTTPStatus

from django.conf import settings
from pytest_django.asserts import assertTemplateUsed


class TemplateOkMixin:
    """Mixin for tests that verify the correct template is used.

    Note: Using this requires the test class to define:
        - A `_get_url` method
        - A `_template_name` variable
    """

    def test_template_used(self, admin_client):
        """Test the correct template is used by the GET request."""
        with assertTemplateUsed(template_name=self._template_name):
            response = admin_client.get(self._get_url())
        assert response.status_code == HTTPStatus.OK


class LoginRequiredMixin:
    """Mixin for tests that require a user to be logged in.

    Note: Using this requires the test class to define:
        - A `_get_url` method
    """

    def test_login_required(self, client):
        """Test for redirect to the login page if the user is not logged in."""
        response = client.get(self._get_url())
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == settings.LOGIN_URL + "?next=" + self._get_url()


class PermissionRequiredMixin(LoginRequiredMixin):
    """Mixin for tests that require authentication and correct user permissions.

    Note: Using this requires the test class to define:
        - A `_get_url` method
    """

    def test_permission_denied(self, client_no_permissions):
        """Test authenticated users missing permissions are blocked."""
        response = client_no_permissions.get(self._get_url())
        assert response.status_code == HTTPStatus.FORBIDDEN  # TODO: check url
