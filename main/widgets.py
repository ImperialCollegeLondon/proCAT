"""Widgets to be used to interact with the plots."""

from datetime import date, datetime, timedelta

from bokeh.models import CustomJS
from bokeh.models.widgets import Button, DatePicker
from bokeh.plotting import figure


def date_picker(
    title: str, default_date: date, min_date: date, max_date: date
) -> DatePicker:
    """Provides a Date Picker widget to select dates in the plots.

    Args:
        title: Title to display above the Date Picker.
        default_date: The initial date to display
        min_date: The earliest possible date the user can select
        max_date: The latest possible date the user can select

    Returns:
        The initialised Date Picker widget.
    """
    picker = DatePicker(
        title=title,
        value=default_date,
        min_date=min_date,
        max_date=max_date,
    )
    return picker


def add_timeseries_callback_to_date_pickers(
    start_picker: DatePicker, end_picker: DatePicker, plot: figure
) -> None:
    """Add the JS callback to start and end date pickers to update a plot x_range.

    Args:
        start_picker: The start date picker to add the callback to
        end_picker: The end date picker to add the callback to
        plot: The plot modified by the date pickers
    """
    # JS code dictates what happens when a new date is selected on the pickers
    callback = CustomJS(
        args=dict(
            start_picker=start_picker, end_picker=end_picker, x_range=plot.x_range
        ),
        code="""const start = Date.parse(start_picker.value);
            const end = Date.parse(end_picker.value);
            x_range.start = start
            x_range.end = end""",
    )  # x_range in the plot is updated with dates parsed from the date pickers
    start_picker.js_on_change("value", callback)
    end_picker.js_on_change("value", callback)


def add_bar_callback_to_date_pickers(
    start_picker: DatePicker,
    end_picker: DatePicker,
    plot: figure,
    chart_months: list[str],
) -> None:
    """Add the JS callback to start and end date pickers to update a bar plot x_range.

    As the x-range is categorical, we supply the list of formatted chart_months, index
    the list using the dates selected in the date pickers, and use the indexed list to
    update x_range.factors. '(window.skip_bar_picker_callback)' is used to prevent
    interference when the plot is updated using the buttons (otherwise when the buttons
    update the date pickers, this callback is also run).

    Args:
        start_picker: The start date picker to add the callback to
        end_picker: The end date picker to add the callback to
        plot: The plot modified by the date pickers
        chart_months: list of months for x-axis in bar chart
    """
    # JS code dictates what happens when a new date is selected on the pickers
    callback = CustomJS(
        args=dict(
            start_picker=start_picker,
            end_picker=end_picker,
            plot=plot,
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
    )  # x_range in the plot is updated with dates parsed from the date pickers

    start_picker.js_on_change("change", callback)
    end_picker.js_on_change("change", callback)


def get_plot_date_pickers(
    min_date: date,
    max_date: date,
    default_start: date,
    default_end: date,
) -> tuple[DatePicker, DatePicker]:
    """Get start and end date pickers for a timeseries plot.

    Creates separate date pickers to choose the start and end date to use as the x_range
    for a plot. Both pickers are provided with a default date to display and minimum
    and maximum possible dates that the user can select.

    Args:
        min_date: The earliest possible date the user can select
        max_date: The latest possible date the user can select
        default_start: The default date to display in the start picker
        default_end: The default date to display in the end picker

    Returns: A tuple of date pickers for selecting the start and end dates of

    """
    start_picker = date_picker(
        title="Select start date:",
        default_date=default_start,
        min_date=min_date,
        max_date=max_date,
    )
    end_picker = date_picker(
        title="Select end date:",
        default_date=default_end,
        min_date=min_date,
        max_date=max_date,
    )

    return start_picker, end_picker


def add_callback_to_button(
    button: Button,
    dates: tuple[datetime, datetime],
    plot: figure,
    start_picker: DatePicker,
    end_picker: DatePicker,
    include_future_dates: bool = True,
) -> None:
    """Add the JS callback to a button to update a plot x_range and picker dates.

    If future dates are not included (e.g. for cost recovery plots), the end date of
    the x_range is the last day of the previous month.

    Args:
        button: The button to add the callback to
        dates: Tuple of datetimes used to update the plot x_range
        plot: The plot the button will be used to update
        start_picker: The start date picker to update
        end_picker: The end date picker to update
        include_future_dates: Whether to include future dates in the timeseries plot
    """
    # JS code dictates what happens when the button is clicked
    end_date = (
        dates[1]
        if include_future_dates
        else (datetime.today()).replace(day=1) - timedelta(days=1)
    )

    button.js_on_click(
        CustomJS(
            args=dict(
                start=dates[0],
                end=end_date,
                # Picker values are set using date in isoformat
                start_isoformat=dates[0].isoformat().split("T")[0],
                end_isoformat=end_date.isoformat().split("T")[0],
                x_range=plot.x_range,
                start_picker=start_picker,
                end_picker=end_picker,
            ),
            code="""x_range.start = start;
            x_range.end = end;
            start_picker.value = start_isoformat;
            end_picker.value = end_isoformat;""",
        )  # x_range in plot and dates displayed in pickers are updated
    )


def add_bar_callback_to_button(
    button: Button,
    dates: tuple[datetime, datetime],
    plot: figure,
    chart_months: list[str],
) -> None:
    """Add the JS callback to a button to update a plot x_range and picker dates.

    'window.skip_bar_picker_callback = true' is used to prevent the callback in
    add_bar_callback_to_date_pickers from being run concurrently.

    Args:
        button: The button to add the callback to
        dates: Tuple of datetimes used to update the plot x_range
        plot: The plot the button will be used to update
        chart_months: list of months for x-axis in bar chart
    """
    # Get formatted dates to use as x-range in plot
    start_tick = f"{dates[0].strftime('%b')} {dates[0].year}"
    end_tick = f"{dates[1].strftime('%b')} {dates[1].year}"

    start = chart_months.index(start_tick)
    end = chart_months.index(end_tick) + 1 if end_tick in chart_months else None
    indexed_months = chart_months[start:end]

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
