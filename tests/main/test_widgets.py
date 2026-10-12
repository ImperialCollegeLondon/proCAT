"""Test suite for the plot widgets."""

from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from django.utils import timezone


@pytest.mark.django_db
def test_add_callback_to_button():
    """Test the add_callback_to_button function."""
    from main import plots, utils, widgets

    button = Button(label="button")

    min_date, max_date = timezone.now(), timezone.now() + timedelta(365)
    dates = utils.get_month_dates_for_previous_years()
    min_date = datetime.combine(dates[0][0], time.min)
    max_date = datetime.combine(dates[-1][1], time.min)
    start = datetime.combine(dates[-12][0], time.min)
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]

    plot, _ = plots.create_cost_recovery_plots(
        dates, min_date, max_date, (start, max_date), chart_months
    )

    expected_callback = CustomJS(
        args=dict(
            start=dates[0][0],
            end=dates[-1][1],
            x_range=plot.x_range,
        ),
        code="""x_range.start = start;
            x_range.end = end;""",
    )

    # Check js_on_click called with the expected arguments
    with patch.object(Button, "js_on_click") as js_mock:
        widgets.add_callback_to_button(button, (dates[0][0], dates[-1][1]), plot)
        js_mock.assert_called_once()

        called_arg = js_mock.call_args.args[0]
        assert called_arg.args == expected_callback.args
        assert called_arg.code == expected_callback.code


@pytest.mark.django_db
def test_add_bar_callback_to_button():
    """Test the add_bar_callback_to_button function."""
    from main import plots, utils, widgets

    dates = utils.get_month_dates_for_previous_years()
    min_date = datetime.combine(dates[0][0], time.min)
    max_date = datetime.combine(dates[-1][1], time.min)
    start = datetime.combine(dates[-12][0], time.min)
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]

    _, bar_plot = plots.create_cost_recovery_plots(
        dates, min_date, max_date, (start, max_date), chart_months
    )
    button = Button(label="button")

    calendar_dates = utils.get_calendar_year_dates()
    end_month = f"{calendar_dates[1].strftime('%b')} {calendar_dates[1].year}"
    start_month = f"{calendar_dates[0].strftime('%b')} {calendar_dates[0].year}"
    idxs = (
        chart_months.index(start_month) if start_month in chart_months else None,
        chart_months.index(end_month) if end_month in chart_months else None,
    )
    expected_callback = CustomJS(
        args=dict(
            indexed_months=chart_months[idxs[0] : idxs[1]]
            if idxs != (None, None)
            else [],
            plot=bar_plot,
        ),
        code="""window.skip_bar_picker_callback = true;
            plot.x_range.factors = indexed_months;""",
    )

    # Check js_on_click called with the expected arguments
    with patch.object(Button, "js_on_click") as js_mock:
        widgets.add_bar_callback_to_button(
            button, calendar_dates, bar_plot, chart_months
        )
        js_mock.assert_called_once()

        called_arg = js_mock.call_args.args[0]
        assert called_arg.args == expected_callback.args
        assert called_arg.code == expected_callback.code
