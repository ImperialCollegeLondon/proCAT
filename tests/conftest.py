"""Pytest configuration file."""

from datetime import datetime, timedelta

import pytest
from django.test import Client


@pytest.fixture
def user(django_user_model):
    """Provides a Django user with predefined attributes."""
    return django_user_model.objects.create_user(
        first_name="test",
        last_name="user",
        email="test.user@mail.com",
        password="1234",
        username="testuser",
    )


@pytest.fixture
def auth_client(user) -> Client:
    """Return an authenticated client."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def department():
    """Provides a default department object."""
    from main import models

    return models.Department.objects.get_or_create(name="ICT", faculty="Other")[0]


@pytest.fixture
def project(user, department):
    """Provides a default project object."""
    from main import models

    return models.Project.objects.get_or_create(
        name="ProCAT",
        department=department,
        lead=user,
        start_date=datetime.now().date(),
        end_date=datetime.now().date() + timedelta(days=42),
        status="Active",
    )[0]


@pytest.fixture
def activity_code():
    """Provides a default activity code object."""
    from main import models

    return models.ActivityCode.objects.get_or_create(
        code="1234", description="Some code", notes="None"
    )[0]


@pytest.fixture
def funding(project, activity_code):
    """Provides a default funding object."""
    from main import models

    return models.Funding.objects.get_or_create(
        project=project,
        source="External",
        funding_body="Funding body",
        project_code="1234",
        activity_code=activity_code,
        expiry_date=datetime.now().date() + timedelta(days=42),
        budget=10000.00,
        daily_rate=389.00,
    )[0]
