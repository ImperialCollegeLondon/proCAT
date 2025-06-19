"""Tests for the plots module."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.usefixtures("project", "funding", "capacity")
def test_calculate_traces():
    """Test function to get plotting data as dataframe."""
    from bokeh.models import ColumnDataSource

    from main import plots

    source = plots.calculate_traces(datetime.now(), datetime.now() + timedelta(365))
    assert isinstance(source, ColumnDataSource)
    assert "Effort" in source.data
    assert "Capacity" in source.data
