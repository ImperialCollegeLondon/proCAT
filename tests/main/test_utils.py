"""Tests for the utils module."""

import pytest


@pytest.mark.django_db
def test_create_destroy_analysis_codes():
    """Roundtrip check of creation and destruction of analysis codes."""
    from main import models, utils

    assert len(models.AnalysisCode.objects.all()) == len(utils.ANALYSIS_CODES)
    utils.destroy_analysis()
    assert len(models.AnalysisCode.objects.all()) == 0
    utils.create_analysis()
    assert len(models.AnalysisCode.objects.all()) == len(utils.ANALYSIS_CODES)
