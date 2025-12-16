"""Context processors for the app."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest


def site_settings(_: HttpRequest) -> dict[str, Any]:  # type: ignore[explicit-any]
    """Site-wide setting options to be passed to the template."""
    return {"use_OIDC": settings.USE_OIDC}
