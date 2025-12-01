"""Pytest configuration file."""

from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone


@pytest.fixture(autouse=True)
def use_model_backend(settings):
    """Ensure the model backend is used for authentication in tests."""
    settings.AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)
    settings.LOGIN_URL = "/accounts/login/"


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
def project_static(user, department, analysis_code):
    """Provides a default project object."""
    from main import models

    project = models.Project.objects.get_or_create(
        name="ProCATv2",
        department=department,
        lead=user,
        start_date=datetime(2025, 1, 1).date(),
        end_date=datetime(2027, 6, 30).date(),
        status="Active",
    )[0]

    _ = models.Funding.objects.get_or_create(
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

    return project


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
def phase(project_static):
    """Provides a default ProjectPhase object."""
    from main import models

    models.ProjectPhase.objects.get_or_create(
        project=project_static,
        value=1,
        start_date=datetime(2027, 4, 10).date(),
        end_date=datetime(2027, 6, 30).date(),
    )

    models.Funding.objects.get_or_create(project=project_static)

    return models.ProjectPhase.objects.get_or_create(
        project=project_static,
        value=1,
        start_date=datetime(2027, 3, 10).date(),
        end_date=datetime(2027, 4, 10).date(),
    )[0]


@pytest.fixture
def client_no_permissions(client, db):
    """Provides a client logged in as a user without permissions."""
    User = get_user_model()
    user = User.objects.create_user(
        username="noperms", email="noperms@example.com", password="x"
    )
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    return client
