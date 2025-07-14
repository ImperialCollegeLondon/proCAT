"""Tests for the plots module."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.usefixtures("project", "funding", "capacity")
def test_calculate_capacity_planning_traces():
    """Test function to get plotting data as dataframe."""
    from bokeh.models import ColumnDataSource

    from main import plots

    source = plots.calculate_capacity_planning_traces(
        datetime.now(), datetime.now() + timedelta(365)
    )
    assert isinstance(source, ColumnDataSource)
    assert "Effort" in source.data
    assert "Capacity" in source.data


@pytest.mark.usefixtures("project", "funding", "capacity")
def test_create_capacity_planning_plot():
    """Test function to create a timeseries plot."""
    from bokeh.plotting import figure

    from main import plots

    plot = plots.create_capacity_planning_plot(
        datetime.now(), datetime.now() + timedelta(365)
    )
    assert isinstance(plot, figure)

    title = "Project effort and team capacity over time"
    assert plot.title.text == title
    assert plot.yaxis.axis_label == "Value"
    assert plot.xaxis.axis_label == "Date"

    legend_items = [item.label.value for item in plot.legend.items]
    assert "Project effort" in legend_items
    assert "Capacity" in legend_items
