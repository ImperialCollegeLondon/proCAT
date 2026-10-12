"""Widgets to be used to interact with the plots."""

from datetime import datetime, timedelta

from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from bokeh.plotting import figure
from django.utils import timezone


def add_callback_to_button(
    button: Button,
    dates: tuple[datetime, datetime],
    plot: figure,
    include_future_dates: bool = True,
) -> None:
    """Add the JS callback to a button to update a plot x_range.

    If future dates are not included (e.g. for cost recovery plots), the end date of
    the x_range is the last day of the previous month.

    Args:
        button: The button to add the callback to
        dates: Tuple of datetimes used to update the plot x_range
        plot: The plot the button will be used to update
        include_future_dates: Whether to include future dates in the timeseries plot
    """
    # JS code dictates what happens when the button is clicked
    end_date = (
        dates[1]
        if include_future_dates
        else (timezone.now()).replace(day=1) - timedelta(days=1)
    )

    button.js_on_click(
        CustomJS(
            args=dict(
                start=dates[0],
                end=end_date,
                x_range=plot.x_range,
            ),
            code="""x_range.start = start;
            x_range.end = end;""",
        )
    )


def add_bar_callback_to_button(
    button: Button,
    dates: tuple[datetime, datetime],
    plot: figure,
    chart_months: list[str],
) -> None:
    """Add the JS callback to a button to update a plot x_range.

    Args:
        button: The button to add the callback to
        dates: Tuple of datetimes used to update the plot x_range
        plot: The plot the button will be used to update
        chart_months: list of months for x-axis in bar chart
    """
    # Get formatted dates to use as x-range in plot
    start_tick = f"{dates[0].strftime('%b')} {dates[0].year}"
    end_tick = f"{dates[1].strftime('%b')} {dates[1].year}"

    start = chart_months.index(start_tick) if start_tick in chart_months else None
    end = chart_months.index(end_tick) + 1 if end_tick in chart_months else None
    indexed_months = (
        chart_months[start:end] if start is not None or end is not None else []
    )

    # JS code dictates what happens when the button is clicked
    button.js_on_click(
        CustomJS(
            args=dict(
                indexed_months=indexed_months,
                plot=plot,
            ),
            code="""window.skip_bar_picker_callback = true;
            plot.x_range.factors = indexed_months;""",
        )  # x_range in plot updated
    )
