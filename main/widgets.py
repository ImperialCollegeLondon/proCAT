"""Widgets to be used to interact with the plots."""

from datetime import date, datetime

from bokeh.models import CustomJS
from bokeh.models.widgets import Button, DatePicker, MultiChoice
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
                # Picker values are set using date in isoformat
                start_isoformat=dates[0].isoformat().split("T")[0],
                end_isoformat=dates[1].isoformat().split("T")[0],
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


def get_combined_callback(
    plot: figure,
    project_multichoice: MultiChoice,
    user_multichoice: MultiChoice,
    start_picker: DatePicker,
    end_picker: DatePicker,
    min_date: date,
    max_date: date,
) -> None:
    """Get the combined code to update plot with the projects and users."""
    callback = CustomJS(
        args=dict(
            plot=plot,
            project_multichoice=project_multichoice,
            user_multichoice=user_multichoice,
            start_picker=start_picker,
            end_picker=end_picker,
            min_date=min_date,
            max_date=max_date,
        ),
        code="""
            console.log("Use projects:", project_multichoice.value);
            console.log("Use users:", user_multichoice.value);

            // Get the data source from the plot
            var source = plot.renderers[0].data_source;
            var original_data = source.data;

            // Get current selections
            var use_projects = project_multichoice.value;
            var use_users = user_multichoice.value;

            // If nothing selected, use all available projects/users
            if (use_projects.length === 0) {
                use_projects = project_multichoice.options.map(opt => opt[0]);
            }
            if (use_users.length === 0) {
                use_users = user_multichoice.options.map(opt => opt[0]);
            }

            // Function to aggregate effort data for use projects
            function aggregateEffort(data, projects) {
                var dates = data['index'];
                var total_effort = new Array(dates.length).fill(0);

                // Sum up effort from use projects
                projects.forEach(function(project) {
                    // Assuming project columns are named 'effort_ProjectName'
                    var project_key = 'effort_' + project;
                    if (data[project_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_effort[i] += data[project_key][i] || 0;
                        }
                    }
                });

                return total_effort;
            }

            // Function to aggregate capacity data for use users
            function aggregateCapacity(data, users) {
                var dates = data['index'];
                var total_capacity = new Array(dates.length).fill(0);

                // Sum up capacity from use users
                users.forEach(function(user) {
                    // Assuming user columns are named 'capacity_UserName'
                    var user_key = 'capacity_' + user;
                    if (data[user_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_capacity[i] += data[user_key][i] || 0;
                        }
                    }
                });

                return total_capacity;
            }

            // Calculate aggregated data
            var aggregated_effort = aggregateEffort(original_data, use_projects);
            var aggregated_capacity = aggregateCapacity(original_data, use_users);

            // Update the data source with aggregated values
            var new_data = {};
            new_data['index'] = original_data['index'];
            new_data['Total effort'] = aggregated_effort;
            new_data['Total Capacity'] = aggregated_capacity;

            // Update the plot
            source.data = new_data;
            source.change.emit();
        """,
    )
    # Attach callbacks to multichoice widgets
    project_multichoice.js_on_change("value", callback)
    user_multichoice.js_on_change("value", callback)


def get_reset_project_callback(
    project_multichoice: MultiChoice,
    user_multichoice: MultiChoice,
    plot: figure,
) -> CustomJS:
    """Get the JS code to reset the project multichoice widget and update plot."""
    return CustomJS(
        args=dict(
            project_multichoice=project_multichoice,
            user_multichoice=user_multichoice,
            plot=plot,
        ),
        code="""
            // Reset the project multichoice widget
            project_multichoice.value = [];  // Reset empty implying all values selected

            // Get the data source from the plot
            var source = plot.renderers[0].data_source;
            var original_data = source.data;

            // Get current selections after reset
            var use_projects = project_multichoice.value;
            var use_users = user_multichoice.value;

            // If nothing selected, use all available projects/users
            if (use_projects.length === 0) {
                use_projects = project_multichoice.options.map(opt => opt[0]);
            }
            if (use_users.length === 0) {
                use_users = user_multichoice.options.map(opt => opt[0]);
            }

            // Function to aggregate effort data for use projects
            function aggregateEffort(data, projects) {
                var dates = data['index'];
                var total_effort = new Array(dates.length).fill(0);

                // Sum up effort from use projects
                projects.forEach(function(project) {
                    var project_key = 'effort_' + project;
                    if (data[project_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_effort[i] += data[project_key][i] || 0;
                        }
                    }
                });

                return total_effort;
            }

            // Function to aggregate capacity data for use users
            function aggregateCapacity(data, users) {
                var dates = data['index'];
                var total_capacity = new Array(dates.length).fill(0);

                // Sum up capacity from use users
                users.forEach(function(user) {
                    var user_key = 'capacity_' + user;
                    if (data[user_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_capacity[i] += data[user_key][i] || 0;
                        }
                    }
                });

                return total_capacity;
            }

            // Calculate aggregated data
            var aggregated_effort = aggregateEffort(original_data, use_projects);
            var aggregated_capacity = aggregateCapacity(original_data, use_users);

            // Update the data source with aggregated values
            var new_data = {};
            new_data['index'] = original_data['index'];
            new_data['Total effort'] = aggregated_effort;
            new_data['Total Capacity'] = aggregated_capacity;

            // Update the plot
            source.data = new_data;
            source.change.emit();
        """,
    )


def get_reset_user_callback(
    project_multichoice: MultiChoice,
    user_multichoice: MultiChoice,
    plot: figure,
) -> CustomJS:
    """Get the JS code to reset the user multichoice widget and update plot."""
    return CustomJS(
        args=dict(
            project_multichoice=project_multichoice,
            user_multichoice=user_multichoice,
            plot=plot,
        ),
        code="""
            // Reset the user multichoice widget
            user_multichoice.value = [];  // Reset empty implying all values selected

            // Get the data source from the plot
            var source = plot.renderers[0].data_source;
            var original_data = source.data;

            // Get current selections after reset
            var use_projects = project_multichoice.value;
            var use_users = user_multichoice.value;

            // If nothing selected, use all available projects/users
            if (use_projects.length === 0) {
                use_projects = project_multichoice.options.map(opt => opt[0]);
            }
            if (use_users.length === 0) {
                use_users = user_multichoice.options.map(opt => opt[0]);
            }

            // Function to aggregate effort data for use projects
            function aggregateEffort(data, projects) {
                var dates = data['index'];
                var total_effort = new Array(dates.length).fill(0);

                projects.forEach(function(project) {
                    var project_key = 'effort_' + project;
                    if (data[project_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_effort[i] += data[project_key][i] || 0;
                        }
                    }
                });

                return total_effort;
            }

            // Function to aggregate capacity data for use users
            function aggregateCapacity(data, users) {
                var dates = data['index'];
                var total_capacity = new Array(dates.length).fill(0);

                users.forEach(function(user) {
                    var user_key = 'capacity_' + user;
                    if (data[user_key]) {
                        for (var i = 0; i < dates.length; i++) {
                            total_capacity[i] += data[user_key][i] || 0;
                        }
                    }
                });

                return total_capacity;
            }

            // Calculate aggregated data
            var aggregated_effort = aggregateEffort(original_data, use_projects);
            var aggregated_capacity = aggregateCapacity(original_data, use_users);

            // Update the data source with aggregated values
            var new_data = {};
            new_data['index'] = original_data['index'];
            new_data['Total effort'] = aggregated_effort;
            new_data['Total Capacity'] = aggregated_capacity;

            // Update the plot
            source.data = new_data;
            source.change.emit();
        """,
    )
