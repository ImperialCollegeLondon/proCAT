"""Tests for the plots module."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.usefixtures("project", "funding", "capacity")
def test_create_capacity_planning_plot():
    """Test function to create the capacity planning plot."""
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


def test_create_cost_recovery_plot(project, funding):
    """Test function to create the cost recovery plot."""
    from bokeh.models import HoverTool
    from bokeh.plotting import figure

    from main import models, plots

    # Create a Monthly Charge for the plot
    models.MonthlyCharge.objects.create(
        project=project,
        funding=funding,
        amount=100.00,
        date=datetime.today().date() - timedelta(100),
    )
    ts_plot, bar_plot = plots.create_cost_recovery_plots()

    # Test timeseries plot
    assert isinstance(ts_plot, figure)

    first_of_month = datetime.today().date().replace(day=1)
    end_date = (first_of_month - timedelta(days=1)).replace(day=1)
    start_date = first_of_month.replace(year=end_date.year - 1)

    ts_title = (
        f"Team capacity and project charging from {start_date.strftime('%B')} "
        f"{start_date.year} to {end_date.strftime('%B')} {end_date.year}"
    )
    assert ts_plot.title.text == ts_title
    assert ts_plot.yaxis.axis_label == "Value"
    assert ts_plot.xaxis.axis_label == "Date"

    ts_legend_items = [item.label.value for item in ts_plot.legend.items]
    assert "Average project capacity %" in ts_legend_items
    assert "Total capacity used %" in ts_legend_items
    assert "Charged capacity used %" in ts_legend_items

    # Test bar plot
    assert isinstance(bar_plot, figure)

    bar_title = (
        f"Monthly charges from {start_date.strftime('%B')} {start_date.year} "
        f"to {end_date.strftime('%B')} {end_date.year}"
    )
    assert bar_plot.title.text == bar_title
    assert bar_plot.yaxis.axis_label == "Total charge (£)"
    assert bar_plot.xaxis.axis_label == "Month-Year"
    assert isinstance(bar_plot.tools[-1], HoverTool)
