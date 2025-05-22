"""Tests for the utils module."""

import pytest


@pytest.mark.django_db
def test_create_destroy_activity_codes():
    """Roundtrip check of creation and destruction of activity codes."""
    from main import models, utils

    assert len(models.ActivityCode.objects.all()) == len(utils.ACTIVITY_CODES)
    utils.destroy_activities()
    assert len(models.ActivityCode.objects.all()) == 0
    utils.create_activities()
    assert len(models.ActivityCode.objects.all()) == len(utils.ACTIVITY_CODES)
