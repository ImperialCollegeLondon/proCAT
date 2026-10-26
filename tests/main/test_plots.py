"""Tests for the plots module."""

from datetime import datetime, time, timedelta
from math import pi
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.utils import timezone


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

    plot, plot_list = plots.create_capacity_planning_plot(
        timezone.now(), timezone.now() + timedelta(365)
    )
    assert isinstance(plot, figure)
    assert len(plot_list) == 1
    for plt in plot_list:
        assert isinstance(plt, figure)

    title = "Project effort and team capacity over time"
    assert plot.title.text == title
    assert plot.yaxis.axis_label == "Value"
    assert plot.xaxis.axis_label == "Date"

    legend_items = [item.label.value for item in plot.legend.items]
    assert "Active project effort" in legend_items
    assert "Maintenance project effort" in legend_items
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
        date=timezone.now().date() - timedelta(100),
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


@patch("main.plots.figure")
@patch("main.plots.HoverTool")
@patch("main.plots.cumsum")
def test_create_pie_chart(cumsum_mock, hovertool_mock, figure_mock):
    """Test the create_pie_chart function."""
    from bokeh.palettes import Category20c

    from main.plots import create_pie_chart

    # Create raw parameters
    data = {"a": 2, "b": 5, "c": 11, "d": 3, "e": 7}
    title = "Pie chart title"

    # Create expected intermediary parameters
    category_name = "Pie_chart_title"
    source = (
        pd.Series(data)
        .reset_index(name="value")
        .rename(columns={"index": category_name})
    )
    source = source.sort_values(by=category_name)
    source["angle"] = [val * 2 * pi / 28 for val in (2, 5, 11, 3, 7)]
    source["colour"] = Category20c[len(data)]

    plot_mock = MagicMock()
    figure_mock.return_value = plot_mock
    hovertool = hovertool_mock(tooltips=f"@{category_name}: value")

    # Call the function to generate the plot
    plot = create_pie_chart(title=title, data=data)

    # Check figure created correctly
    figure_mock.assert_called_once_with(
        title=title, toolbar_location=None, x_range=(-0.5, 1.0)
    )

    # Check pie chart created correctly
    plot_mock.wedge.assert_called_once()
    # Need to check arguments individually as source is complex
    plot_mock.wedge.call_args[1]["x"] == 0
    plot_mock.wedge.call_args[1]["y"] == 1
    plot_mock.wedge.call_args[1]["start_angle"] == cumsum_mock(
        "angle", include_zero=True
    )
    plot_mock.wedge.call_args[1]["end_angle"] == cumsum_mock("angle")
    plot_mock.wedge.call_args[1]["radius"] == 0.4
    plot_mock.wedge.call_args[1]["line_color"] == "white"
    plot_mock.wedge.call_args[1]["fill_color"] == "colour"
    plot_mock.wedge.call_args[1]["legend_field"] == "Pie_chart_title"
    pd.testing.assert_frame_equal(plot_mock.wedge.call_args[1]["source"], source)

    # Check hover tool added correctly
    plot_mock.add_tools.assert_called_once_with(hovertool)

    # Check axis properties set correctly
    assert plot.axis.axis_label is None
    assert not plot.axis.visible
    assert plot.grid.grid_line_color is None
