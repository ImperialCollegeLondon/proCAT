"""Pytest configuration file."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone


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
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=42),
        status="Active",
    )[0]


@pytest.fixture
def analysis_code():
    """Provides a default analysis code object."""
    from main import models

    return models.AnalysisCode.objects.get_or_create(
        code="1234", description="Some code", notes="None"
    )[0]


@pytest.fixture
def funding(project, analysis_code):
    """Provides a default funding object."""
    from main import models

    return models.Funding.objects.get_or_create(
        project=project,
        source="External",
        funding_body="Funding body",
        cost_centre="centre",
        activity="G12345",
        analysis_code=analysis_code,
        expiry_date=timezone.now().date() + timedelta(days=42),
        budget=10000.00,
        daily_rate=389.00,
    )[0]


@pytest.fixture
def capacity(user):
    """Provides a default capacity object."""
    from main import models

    return models.Capacity.objects.get_or_create(
        user=user,
        value=0.7,
        start_date=timezone.now().date(),
    )


@pytest.fixture
def rse_user(django_user_model):
    """Provides a Django user with the 'RSE' group assigned."""
    user = django_user_model.objects.create_user(
        first_name="rse",
        last_name="user",
        email="rse.user@mail.com",
        password="1234",
        username="rseuser",
    )
    from django.contrib.auth.models import Group

    group, _ = Group.objects.get_or_create(name="RSE")
    user.groups.add(group)
    return user


@pytest.fixture
def rse_auth_client(rse_user) -> Client:
    """Return an authenticated client for a user with the 'RSE' group."""
    client = Client()
    client.force_login(rse_user)
    return client
