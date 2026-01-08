"""Test suite for the plot widgets."""

from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
from bokeh.models import CustomJS
from bokeh.models.widgets import Button, DatePicker
from django.utils import timezone


@pytest.mark.django_db
def test_add_timeseries_callback_to_date_pickers():
    """Test the add_timeseries_callback_to_date_pickers function."""
    from main import plots, widgets

    min_date, max_date = timezone.now(), timezone.now() + timedelta(365)
    display_dates = (min_date + timedelta(100), min_date + timedelta(200))

    plot = plots.create_capacity_planning_plot(
        min_date, max_date, x_range=display_dates
    )

    start_picker, end_picker = widgets.get_plot_date_pickers(
        min_date.date(),
        max_date.date(),
        display_dates[0].date(),
        display_dates[1].date(),
    )

    expected_callback = CustomJS(
        args=dict(
            start_picker=start_picker, end_picker=end_picker, x_range=plot.x_range
        ),
        code="""const start = Date.parse(start_picker.value);
            const end = Date.parse(end_picker.value);
            x_range.start = start
            x_range.end = end""",
    )

    # Check js_on_change called with the expected arguments
    with patch.object(DatePicker, "js_on_change") as js_mock:
        widgets.add_timeseries_callback_to_date_pickers(start_picker, end_picker, plot)
        assert js_mock.call_count == 2

        called_args = js_mock.call_args.args
        assert called_args[0] == "value"
        assert called_args[1].args == expected_callback.args
        assert called_args[1].code == expected_callback.code


@pytest.mark.django_db
def test_add_bar_callback_to_date_pickers():
    """Test the add_bar_callback_to_date_pickers function."""
    from main import plots, utils, widgets

    dates = utils.get_month_dates_for_previous_years()
    min_date = datetime.combine(dates[0][0], time.min)
    max_date = datetime.combine(dates[-1][1], time.min)
    start = datetime.combine(dates[-12][0], time.min)
    chart_months = [f"{date[0].strftime('%b')} {date[0].year}" for date in dates]

    start_picker, end_picker = widgets.get_plot_date_pickers(
        min_date.date(), max_date.date(), start.date(), max_date.date()
    )

    _, bar_plot = plots.create_cost_recovery_plots(
        dates, min_date, max_date, (start, max_date), chart_months
    )

    expected_callback = CustomJS(
        args=dict(
            start_picker=start_picker,
            end_picker=end_picker,
            plot=bar_plot,
            months=chart_months,
        ),
        code="""if (window.skip_bar_picker_callback) {
            window.skip_bar_picker_callback = false;
            return;
        }

        function getIndex(picker_value) {
            const date = new Date(picker_value);
            const month = date.toLocaleString('default', { month: 'short' });
            const year = date.getFullYear();
            const formatted_month = `${month} ${year}`;
            return months.indexOf(formatted_month);
        }

        const start_index = getIndex(start_picker.value);
        const end_index = getIndex(end_picker.value);
        const selected_months = months.slice(start_index, end_index + 1);

        plot.x_range.factors = selected_months;""",
    )

    # Check js_on_change called with the expected arguments
    with patch.object(DatePicker, "js_on_change") as js_mock:
        widgets.add_bar_callback_to_date_pickers(
            start_picker, end_picker, bar_plot, chart_months
        )
        assert js_mock.call_count == 2

        called_args = js_mock.call_args.args
        assert called_args[0] == "change"
        assert called_args[1].args == expected_callback.args
        assert called_args[1].code == expected_callback.code


@pytest.mark.django_db
def test_add_callback_to_button():
    """Test the add_callback_to_button function."""
    from main import plots, utils, widgets

    button = Button(label="button")

    min_date, max_date = timezone.now(), timezone.now() + timedelta(365)
    display_dates = (min_date + timedelta(100), min_date + timedelta(200))
    start_picker, end_picker = widgets.get_plot_date_pickers(
        min_date.date(),
        max_date.date(),
        display_dates[0].date(),
        display_dates[1].date(),
    )

    plot = plots.create_capacity_planning_plot(
        min_date, max_date, x_range=display_dates
    )
    calendar_dates = utils.get_calendar_year_dates()

    expected_callback = CustomJS(
        args=dict(
            start=calendar_dates[0],
            end=calendar_dates[1],
            start_isoformat=calendar_dates[0].isoformat().split("T")[0],
            end_isoformat=calendar_dates[1].isoformat().split("T")[0],
            x_range=plot.x_range,
            start_picker=start_picker,
            end_picker=end_picker,
        ),
        code="""x_range.start = start;
            x_range.end = end;
            start_picker.value = start_isoformat;
            end_picker.value = end_isoformat;""",
    )

    # Check js_on_click called with the expected arguments
    with patch.object(Button, "js_on_click") as js_mock:
        widgets.add_callback_to_button(
            button, calendar_dates, plot, start_picker, end_picker
        )
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
