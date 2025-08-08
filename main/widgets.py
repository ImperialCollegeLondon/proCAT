"""Widgets to be used to interact with the plots."""

from datetime import date, datetime

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
) -> None:
    """Add the JS callback to a button to update a plot x_range and picker dates.

    Args:
        button: The button to add the callback to
        dates: Tuple of datetimes used to update the plot x_range
        plot: The plot the button will be used to update
        start_picker: The start date picker to update
        end_picker: The end date picker to update
    """
    # JS code dictates what happens when the button is clicked
    button.js_on_click(
        CustomJS(
            args=dict(
                start=dates[0],
                end=dates[1],
                x_range=plot.x_range,
                start_picker=start_picker,
                end_picker=end_picker,
            ),
            code="""x_range.start = start;
            x_range.end = end;
            start_picker.value = new Date(start).toISOString().split('T')[0];
            end_picker.value = new Date(end).toISOString().split('T')[0];""",
        )  # x_range in plot and dates displayed in pickers are updated
    )


def get_button(
    label: str,
) -> Button:
    """Get button widget.

    Args:
        label: Label to display on the button

    Returns:
        A Bokeh button that can be used to update the x_range shown in a plot.
    """
    button = Button(label=label)
    return button
