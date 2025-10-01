"""Tests for the plots module."""

from datetime import datetime, time, timedelta
from unittest.mock import patch

import pandas as pd
import pytest


def test_add_varea_glyph():
    """Test function to add a varea glyph to a plot."""
    from main.plots import add_varea_glyph

    with patch("main.plots.figure") as plot_mock:
        with patch("main.plots.ColumnDataSource") as source_mock:
            df = pd.DataFrame(
                {
                    "index": list(range(10)),
                    "upper": [5, 5, 5, 3, 3, 7, 2, 10, 10, 12],
                    "lower": [3, 3, 7, 7, 4, 4, 4, 12, 9, 9],
                }
            )
            expected_series = pd.Series([5, 5, 7, 7, 4, 7, 4, 12, 10, 12])

            add_varea_glyph(plot_mock, df, "upper", "lower", "green")

            args = source_mock.call_args[0]
            pd.testing.assert_series_equal(df["index"], args[0]["index"])
            pd.testing.assert_series_equal(df["lower"], args[0]["y1"])
            pd.testing.assert_series_equal(
                expected_series, args[0]["y2"], check_names=False
            )


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
    assert "Active project effort" in legend_items
    assert "Confirmed project effort" in legend_items
    assert "Tentative project effort" in legend_items
    assert "Capacity" in legend_items


def test_create_cost_recovery_plot(project, funding):
    """Test function to create the cost recovery plot."""
    from bokeh.models import HoverTool
    from bokeh.plotting import figure

    from main import models, plots, utils

    # Create a Monthly Charge for the plot
    models.MonthlyCharge.objects.create(
        project=project,
        funding=funding,
        amount=100.00,
        date=datetime.today().date() - timedelta(100),
    )

    # Create cost recovery plots
    dates = utils.get_month_dates_for_previous_years()
    min_date = datetime.combine(dates[0][0], time.min)
    max_date = datetime.combine(dates[-1][1], time.min)
    start = datetime.combine(dates[-12][0], time.min)
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]
    ts_plot, bar_plot = plots.create_cost_recovery_plots(
        dates, min_date, max_date, (start, max_date), chart_months
    )

    # Test timeseries plot
    assert isinstance(ts_plot, figure)
    ts_title = "Team capacity and project charging over time"
    assert ts_plot.title.text == ts_title
    assert ts_plot.yaxis.axis_label == "Value"
    assert ts_plot.xaxis.axis_label == "Date"

    ts_legend_items = [item.label.value for item in ts_plot.legend.items]
    assert "Average capacity for project work %" in ts_legend_items
    assert "Fraction of capacity used for all projects %" in ts_legend_items
    assert "Fraction of capacity used for charged projects %" in ts_legend_items

    # Test bar plot
    assert isinstance(bar_plot, figure)

    bar_title = "Total monthly charges"
    assert bar_plot.title.text == bar_title
    assert bar_plot.yaxis.axis_label == "Total charge (£)"
    assert bar_plot.xaxis.axis_label == "Month-Year"
    assert isinstance(bar_plot.tools[-1], HoverTool)
