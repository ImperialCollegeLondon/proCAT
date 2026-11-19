"""Tests for the plots module."""

from datetime import date, datetime, time, timedelta
from math import pi
from unittest.mock import MagicMock, call, patch

import pandas as pd
from django.utils import timezone


class TestCapacityTimeseriesPlotting:
    """Tests for the capacity timeseries plotting functions."""

    def setup_method(self):
        """Define some basic variables for reuse when creating plots."""
        self.start_date = date(2026, 11, 18)
        self.end_date = date(2026, 11, 19)
        self.traces = [
            {
                "timeseries": pd.Series({self.start_date: 12, self.end_date: 34}),
                "colour": "red",
                "label": "red data",
            },
            {
                "timeseries": pd.Series({self.start_date: 56, self.end_date: 78}),
                "colour": "green",
                "label": "green data",
            },
            {
                "timeseries": pd.Series({self.start_date: 98, self.end_date: 76}),
                "colour": "blue",
                "label": "blue data",
            },
        ]
        self.capacities = pd.DataFrame(
            {trace["colour"]: trace["timeseries"].values for trace in self.traces},
            index=(self.start_date, self.end_date),
        )

    def test_create_timeseries_plot_base(self):
        """Test the _create_timeseries_plot_base function.

        Function creates the ColumnDataSource data structure and the figure, but doesn't
        actually plot the data. Check data structure and figure created as expected.
        """
        from bokeh.models import PanTool, ResetTool, SaveTool, WheelZoomTool
        from numpy import array

        from main.plots import _create_timeseries_plot_base

        # Call the function
        source, plot = _create_timeseries_plot_base(
            title="Test plot",
            traces=self.traces,
            x_range=(self.start_date, self.end_date),
            height=250,
        )

        # Check source is as expected
        assert (
            source.data["index"]
            == array([self.start_date, self.end_date], dtype=object)
        ).all()
        assert (source.data["red data"] == array([12, 34])).all()
        assert (source.data["green data"] == array([56, 78])).all()
        assert (source.data["blue data"] == array([98, 76])).all()

        # Check plot is as expected
        assert plot.title.text == "Test plot"
        assert plot.height == 250
        assert plot.background_fill_color == "#efefef"
        assert isinstance(plot.tools[0], SaveTool)
        assert isinstance(plot.tools[1], PanTool)
        assert isinstance(plot.tools[2], WheelZoomTool)
        assert isinstance(plot.tools[3], ResetTool)
        assert plot.sizing_mode == "stretch_width"
        assert plot.x_range.start == self.start_date
        assert plot.x_range.end == self.end_date
        assert plot.yaxis.axis_label == "Value"
        assert plot.xaxis.axis_label == "Date"

    @patch("main.plots._create_timeseries_plot_base")
    def test_create_timeseries_stacked(self, plot_base_mock):
        """Test the create_timeseries_stacked function."""
        # Set up the source and base figure
        from main.plots import create_timeseries_stacked

        source_mock = MagicMock()
        plot_mock = MagicMock()
        plot_base_mock.return_value = (source_mock, plot_mock)

        # Call the function
        source, plot = create_timeseries_stacked(
            title="Test plot",
            traces=self.traces,
            x_range=(self.start_date, self.end_date),
            height=250,
            legend_loc="top_right",
        )
        assert source is source_mock

        # Check varea_stack called as expected
        data_to_stack = [trace["label"] for trace in self.traces]
        colours = [trace["colour"] for trace in self.traces]
        plot_mock.varea_stack.assert_called_once_with(
            data_to_stack,
            x="index",
            source=source_mock,
            fill_color=colours,
            fill_alpha=0.3,
        )

        # Check vline_stack called as expected
        plot_mock.vline_stack.assert_called_once_with(
            data_to_stack,
            x="index",
            source=source_mock,
            line_width=2,
            color=colours,
            legend_label=data_to_stack,
        )

        assert plot.legend.location == "top_right"

    @patch("main.plots.create_timeseries_stacked")
    @patch("main.plots.HoverTool")
    def test_create_capacity_timeseries_plot(
        self, hover_tool_mock, create_timeseries_stacked_mock
    ):
        """Test the _create_capacity_timeseries_plot function."""
        from main.plots import _create_capacity_timeseries_plot

        effort = pd.Series({self.start_date: 123, self.end_date: 456})
        capacity = pd.Series({self.start_date: 987, self.end_date: 654})

        source_mock = MagicMock()
        plot_mock = MagicMock()
        create_timeseries_stacked_mock.return_value = (source_mock, plot_mock)

        capacity_line = MagicMock()
        plot_mock.line.return_value = capacity_line

        tooltips = [
            ("Date", "@{index}{%F}"),
            ("red data", "@{red data}{0.00}"),
            ("green data", "@{green data}{0.00}"),
            ("blue data", "@{blue data}{0.00}"),
            ("Capacity", "@{Capacity}{0.00}"),
        ]

        hover_tool = MagicMock()
        hover_tool_mock.return_value = hover_tool

        # Call the function
        plot = _create_capacity_timeseries_plot(
            title="Test plot",
            traces=self.traces,
            aggregated_effort=effort,
            capacity=capacity,
            x_range=(self.start_date, self.end_date),
            height=999,
            legend_loc="bottom_right",
        )

        # Check internal functions called as expected
        # Traces updated and plot created
        self.traces.append(
            {
                "timeseries": pd.Series(
                    {self.start_date: 987 - 123, self.end_date: 654 - 456}
                ),
                "colour": "darkgreen",
                "label": "Capacity",
            }
        )
        create_timeseries_stacked_mock.assert_called_once()
        assert create_timeseries_stacked_mock.call_args.kwargs["title"] == "Test plot"
        for i in range(len(self.traces)):
            assert (
                create_timeseries_stacked_mock.call_args.kwargs["traces"][i][
                    "timeseries"
                ]
                == self.traces[i]["timeseries"]
            ).all()
        assert create_timeseries_stacked_mock.call_args.kwargs["x_range"] == (
            self.start_date,
            self.end_date,
        )
        assert create_timeseries_stacked_mock.call_args.kwargs["height"] == 999
        assert (
            create_timeseries_stacked_mock.call_args.kwargs["legend_loc"]
            == "bottom_right"
        )

        # Capacity line removed, replaced with total capacity, and then plotted
        plot.renderers.pop.assert_called_once()
        assert source_mock.add.call_args_list[0][0] == ([987, 654], "Total capacity")

        plot_mock.line.assert_called_once_with(
            "index",
            "Total capacity",
            source=source_mock,
            line_width=2,
            color="darkgreen",
            legend_label="Capacity",
        )

        # Hover tool created and added
        hover_tool_mock.assert_called_once_with(
            tooltips=tooltips,
            formatters={"@{index}": "datetime"},
            renderers=[capacity_line],
            mode="vline",
        )
        plot.add_tools.assert_called_once_with(hover_tool)

    @patch("main.plots.timeseries.get_effort_timeseries")
    @patch("main.plots._create_capacity_timeseries_plot")
    def test_create_team_capacity_plot(
        self, create_capacity_timeseries_plot_mock, get_effort_timeseries_mock
    ):
        """Test the create_team_capacity_plot function."""
        from main.plots import create_team_capacity_plot

        effort = (
            pd.Series({self.start_date: 1, self.end_date: 2}),
            pd.Series({self.start_date: 3, self.end_date: 4}),
            pd.Series({self.start_date: 5, self.end_date: 6}),
            pd.Series({self.start_date: 7, self.end_date: 8}),
        )
        get_effort_timeseries_mock.side_effect = effort

        # Call the function
        plot = create_team_capacity_plot(
            self.capacities,
            self.start_date,
            self.end_date,
            (self.start_date, self.end_date),
        )

        # Check plot created as expected
        assert get_effort_timeseries_mock.call_args_list == [
            call(self.start_date, self.end_date, ["Active"]),
            call(self.start_date, self.end_date, ["Maintenance"]),
            call(self.start_date, self.end_date, ["Confirmed"]),
            call(self.start_date, self.end_date, ["Tentative"]),
        ]

        traces_expected = [
            {
                "timeseries": effort[0],
                "colour": "navy",
                "label": "Active project effort",
            },
            {
                "timeseries": effort[1],
                "colour": "purple",
                "label": "Maintenance project effort",
            },
            {
                "timeseries": effort[2],
                "colour": "orange",
                "label": "Confirmed project effort",
            },
            {
                "timeseries": effort[3],
                "colour": "firebrick",
                "label": "Tentative project effort",
            },
        ]
        aggregated_effort = pd.Series({self.start_date: 16, self.end_date: 20})
        aggregated_capacity = pd.Series(
            {self.start_date: 12 + 56 + 98, self.end_date: 34 + 78 + 76}
        )

        create_capacity_timeseries_plot_mock.assert_called_once()
        assert create_capacity_timeseries_plot_mock.call_args.kwargs["title"] == (
            "Project effort and team capacity over time"
        )
        assert create_capacity_timeseries_plot_mock.call_args.kwargs["traces"] == (
            traces_expected
        )
        assert (
            create_capacity_timeseries_plot_mock.call_args.kwargs["aggregated_effort"]
            == aggregated_effort
        ).all()
        assert (
            create_capacity_timeseries_plot_mock.call_args.kwargs["capacity"]
            == aggregated_capacity
        ).all()
        assert create_capacity_timeseries_plot_mock.call_args.kwargs["x_range"] == (
            (self.start_date, self.end_date)
        )

        assert plot.y_range.start == 0
        assert plot.y_range.end == 1.05 * (34 + 78 + 76)

    @patch("main.plots.timeseries.get_allocation_timeseries")
    @patch("main.plots._create_capacity_timeseries_plot")
    def test_create_individual_capacity_plots(
        self, create_capacity_timeseries_plot_mock, get_allocation_timeseries_mock
    ):
        """Test the create_individual_capacity_plots function."""
        from main.plots import PALETTE, create_individual_capacity_plots

        allocations = {
            "red": pd.DataFrame(
                {"yellow": 0.4, "magenta": 0.8}, index=(self.start_date, self.end_date)
            ),
            "green": pd.DataFrame(
                {"cyan": 0.3, "yellow": 0.6}, index=(self.start_date, self.end_date)
            ),
            "blue": pd.DataFrame(
                {"cyan": 0.7, "magenta": 0.2}, index=(self.start_date, self.end_date)
            ),
        }
        get_allocation_timeseries_mock.return_value = allocations

        red_plot = MagicMock()
        green_plot = MagicMock()
        blue_plot = MagicMock()
        create_capacity_timeseries_plot_mock.side_effect = (
            red_plot,
            green_plot,
            blue_plot,
        )

        # Call the function
        plots = create_individual_capacity_plots(
            self.capacities,
            self.start_date,
            self.end_date,
            (self.start_date, self.end_date),
        )

        # Check plots created as expected
        get_allocation_timeseries_mock.assert_called_once_with(
            self.start_date, self.end_date
        )

        traces_expected = [
            {
                "timeseries": allocations["red"]["yellow"],
                "colour": PALETTE[0],
                "label": "yellow",
            },
            {
                "timeseries": allocations["red"]["magenta"],
                "colour": PALETTE[1],
                "label": "magenta",
            },
            {
                "timeseries": allocations["green"]["cyan"],
                "colour": PALETTE[2],
                "label": "cyan",
            },
            {
                "timeseries": allocations["green"]["yellow"],
                "colour": PALETTE[0],
                "label": "yellow",
            },
            {
                "timeseries": allocations["blue"]["cyan"],
                "colour": PALETTE[2],
                "label": "cyan",
            },
            {
                "timeseries": allocations["blue"]["magenta"],
                "colour": PALETTE[1],
                "label": "magenta",
            },
        ]
        aggregated_efforts = {
            "red": pd.Series({self.start_date: 0.4 + 0.8, self.end_date: 0.4 + 0.8}),
            "green": pd.Series({self.start_date: 0.3 + 0.6, self.end_date: 0.3 + 0.6}),
            "blue": pd.Series({self.start_date: 0.7 + 0.2, self.end_date: 0.7 + 0.2}),
        }

        assert create_capacity_timeseries_plot_mock.call_count == 3

        # Check plot titles
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["title"]
            == "red"
        )
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["title"]
            == "green"
        )
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["title"]
            == "blue"
        )

        # Check plot data (complex because of nested data structures...)
        # "red"
        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][0][
                "timeseries"
            ],
            traces_expected[0]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][0][
            "colour"
        ] == traces_expected[0]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][0][
            "label"
        ] == traces_expected[0]["label"]

        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][1][
                "timeseries"
            ],
            traces_expected[1]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][1][
            "colour"
        ] == traces_expected[1]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["traces"][1][
            "label"
        ] == traces_expected[1]["label"]

        # "green"
        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][0][
                "timeseries"
            ],
            traces_expected[2]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][0][
            "colour"
        ] == traces_expected[2]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][0][
            "label"
        ] == traces_expected[2]["label"]

        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][1][
                "timeseries"
            ],
            traces_expected[3]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][1][
            "colour"
        ] == traces_expected[3]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["traces"][1][
            "label"
        ] == traces_expected[3]["label"]

        # "blue"
        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][0][
                "timeseries"
            ],
            traces_expected[4]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][0][
            "colour"
        ] == traces_expected[4]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][0][
            "label"
        ] == traces_expected[4]["label"]

        pd.testing.assert_series_equal(
            create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][1][
                "timeseries"
            ],
            traces_expected[5]["timeseries"],
        )
        create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][1][
            "colour"
        ] == traces_expected[5]["colour"]
        create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["traces"][1][
            "label"
        ] == traces_expected[5]["label"]

        # Check aggregated efforts
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[0].kwargs[
                "aggregated_effort"
            ]
            == aggregated_efforts["red"]
        ).all()
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[1].kwargs[
                "aggregated_effort"
            ]
            == aggregated_efforts["green"]
        ).all()
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[2].kwargs[
                "aggregated_effort"
            ]
            == aggregated_efforts["blue"]
        ).all()

        # Check individual's capacities
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[0].kwargs["capacity"]
            == self.capacities["red"]
        ).all()
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[1].kwargs["capacity"]
            == self.capacities["green"]
        ).all()
        assert (
            create_capacity_timeseries_plot_mock.call_args_list[2].kwargs["capacity"]
            == self.capacities["blue"]
        ).all()

        # Check plot x_range, height and legend location
        for i in range(3):
            assert create_capacity_timeseries_plot_mock.call_args_list[i].kwargs[
                "x_range"
            ] == (self.start_date, self.end_date)
            assert (
                create_capacity_timeseries_plot_mock.call_args_list[i].kwargs["height"]
                == 150
            )
            assert (
                create_capacity_timeseries_plot_mock.call_args_list[i].kwargs[
                    "legend_loc"
                ]
                == "top_right"
            )

        # Check output
        assert len(plots) == 3
        assert plots[0] is red_plot
        assert plots[1] is green_plot
        assert plots[2] is blue_plot


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
    from main.plots import PALETTE, create_pie_chart

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
    source["colour"] = PALETTE[: len(data)]

    plot_mock = MagicMock()
    figure_mock.return_value = plot_mock
    hovertool = hovertool_mock(tooltips=f"@{category_name}: value")

    # Call the function to generate the plot
    plot = create_pie_chart(title=title, data=data)

    # Check figure created correctly
    figure_mock.assert_called_once_with(
        title=title,
        toolbar_location=None,
        x_range=(-0.5, 1.0),
        sizing_mode="stretch_width",
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


@patch("main.plots.analytics")
@patch("main.plots.create_pie_chart")
def test_create_analytics_plots(create_pie_chart_mock, analytics_mock):
    """Test the _create_analytics_plots function."""
    from main.plots import AnalyticsFigure, _create_analytics_plots

    projects = MagicMock()

    proj_per_dept = MagicMock()
    analytics_mock.get_project_count_per_department.return_value = proj_per_dept
    proj_per_fac = MagicMock()
    analytics_mock.get_project_count_per_faculty.return_value = proj_per_fac
    fund_per_dept = MagicMock()
    analytics_mock.get_funding_per_department.return_value = fund_per_dept
    fund_per_fac = MagicMock()
    analytics_mock.get_funding_per_faculty.return_value = fund_per_fac
    fund_per_budget_type = MagicMock()
    analytics_mock.get_funding_per_budget_type.return_value = fund_per_budget_type
    proj_per_funder = MagicMock()
    analytics_mock.get_project_count_per_funding_body.return_value = proj_per_funder
    funds_per_funder = MagicMock()
    analytics_mock.get_funding_per_funding_body.return_value = funds_per_funder

    proj_per_dept_plot = MagicMock()
    proj_per_fac_plot = MagicMock()
    fund_per_dept_plot = MagicMock()
    fund_per_fac_plot = MagicMock()
    fund_per_budget_type_plot = MagicMock()
    proj_per_funder_plot = MagicMock()
    fund_per_funder_plot = MagicMock()

    create_pie_chart_mock.side_effect = (
        proj_per_dept_plot,
        proj_per_fac_plot,
        fund_per_dept_plot,
        fund_per_fac_plot,
        fund_per_budget_type_plot,
        proj_per_funder_plot,
        fund_per_funder_plot,
    )

    plots_expected = [
        AnalyticsFigure(plot=proj_per_dept_plot, group="projects"),
        AnalyticsFigure(plot=proj_per_fac_plot, group="projects"),
        AnalyticsFigure(plot=fund_per_dept_plot, group="funding"),
        AnalyticsFigure(plot=fund_per_fac_plot, group="funding"),
        AnalyticsFigure(plot=fund_per_budget_type_plot, group="budget"),
        AnalyticsFigure(plot=proj_per_funder_plot, group="funder"),
        AnalyticsFigure(plot=fund_per_funder_plot, group="funder"),
    ]

    # Call the function
    plots_actual = _create_analytics_plots(projects)

    # Check analytics functions called as expected
    analytics_mock.get_project_count_per_department.assert_called_once_with(projects)
    analytics_mock.get_project_count_per_faculty.assert_called_once_with(projects)
    analytics_mock.get_funding_per_department.assert_called_once_with(projects)
    analytics_mock.get_funding_per_faculty.assert_called_once_with(projects)
    analytics_mock.get_funding_per_budget_type.assert_called_once_with(projects)
    analytics_mock.get_project_count_per_funding_body.assert_called_once_with(projects)
    analytics_mock.get_funding_per_funding_body.assert_called_once_with(projects)

    # Check plotting functions called as expected
    create_pie_chart_mock.assert_any_call(
        title="Projects per department", data=proj_per_dept
    )
    create_pie_chart_mock.assert_any_call(
        title="Projects per faculty", data=proj_per_fac
    )
    create_pie_chart_mock.assert_any_call(
        title="Funding per department", data=fund_per_dept, tooltip_fmt="£@value{0,0}"
    )
    create_pie_chart_mock.assert_any_call(
        title="Funding per faculty", data=fund_per_fac, tooltip_fmt="£@value{0,0}"
    )
    create_pie_chart_mock.assert_any_call(
        title="Funding per budget type",
        data=fund_per_budget_type,
        tooltip_fmt="£@value{0,0}",
    )
    create_pie_chart_mock.assert_any_call(
        title="Projects per funding body", data=proj_per_funder
    )
    create_pie_chart_mock.assert_any_call(
        title="Funding per funding body",
        data=funds_per_funder,
        tooltip_fmt="£@value{0,0}",
    )

    assert plots_actual == plots_expected


@patch("main.plots.date")
@patch("main.plots.analytics")
@patch("main.plots._create_analytics_plots")
@patch("main.plots.TabPanel")
@patch("main.plots.Tabs")
@patch("main.plots.gridplot")
@patch("main.plots.column")
def test_create_analytics_layout(
    column_mock,
    gridplot_mock,
    tabs_mock,
    tab_panel_mock,
    create_analytics_plots_mock,
    analytics_mock,
    date_mock,
):
    """Test the create_analytics_layout function."""
    from main.plots import AnalyticsFigure, create_analytics_layout

    # Mock the functions called internally
    date_mock.today.return_value = date(2026, 10, 26)

    proj_this_year = MagicMock()
    analytics_mock.get_projects_active_between.return_value = proj_this_year

    proj_per_dept_plot = MagicMock(title=MagicMock(text="Proj per dept", visible=True))
    proj_per_fac_plot = MagicMock(title=MagicMock(text="Proj per fac", visible=True))
    fund_per_dept_plot = MagicMock(title=MagicMock(text="Fund per dept", visible=True))
    fund_per_fac_plot = MagicMock(title=MagicMock(text="Fund per fac", visible=True))
    fund_per_budget_type_plot = MagicMock(
        title=MagicMock(text="Fund per budget type", visible=True)
    )
    proj_per_funder_plot = MagicMock(
        title=MagicMock(text="Proj per funder", visible=True)
    )
    fund_per_funder_plot = MagicMock(
        title=MagicMock(text="Fund per funder", visible=True)
    )

    plots = [
        AnalyticsFigure(plot=proj_per_dept_plot, group="projects"),
        AnalyticsFigure(plot=proj_per_fac_plot, group="projects"),
        AnalyticsFigure(plot=fund_per_dept_plot, group="funding"),
        AnalyticsFigure(plot=fund_per_fac_plot, group="funding"),
        AnalyticsFigure(plot=fund_per_budget_type_plot, group="budget"),
        AnalyticsFigure(plot=proj_per_funder_plot, group="funder"),
        AnalyticsFigure(plot=fund_per_funder_plot, group="funder"),
    ]

    create_analytics_plots_mock.return_value = plots

    projects_tabs = MagicMock()
    funding_tabs = MagicMock()
    budget_tabs = MagicMock()
    funder_tabs = MagicMock()

    tabs_mock.side_effect = (projects_tabs, funding_tabs, budget_tabs, funder_tabs)

    gridplot = MagicMock()
    gridplot_mock.return_value = gridplot

    layout_expected = MagicMock()
    column_mock.return_value = layout_expected

    # Call the function
    layout_actual = create_analytics_layout()

    # Check list of projects retrieved as expected
    analytics_mock.get_projects_active_between.assert_called_once_with(
        date(2025, 10, 26), date(2026, 10, 26)
    )

    # Check plot generating function called as expected
    create_analytics_plots_mock.assert_called_once_with(proj_this_year)

    assert all([not plot.plot.title.visible for plot in plots])

    # Check plots arranged into tabs as expected
    tab_panel_mock.assert_any_call(
        title=proj_per_dept_plot.title.text, child=proj_per_dept_plot
    )
    tab_panel_mock.assert_any_call(
        title=proj_per_fac_plot.title.text, child=proj_per_fac_plot
    )
    tab_panel_mock.assert_any_call(
        title=fund_per_dept_plot.title.text, child=fund_per_dept_plot
    )
    tab_panel_mock.assert_any_call(
        title=fund_per_fac_plot.title.text, child=fund_per_fac_plot
    )
    tab_panel_mock.assert_any_call(
        title=fund_per_budget_type_plot.title.text, child=fund_per_budget_type_plot
    )
    tab_panel_mock.assert_any_call(
        title=proj_per_funder_plot.title.text, child=proj_per_funder_plot
    )
    tab_panel_mock.assert_any_call(
        title=fund_per_funder_plot.title.text, child=fund_per_funder_plot
    )

    # Check layout created as expected
    gridplot_mock.assert_called_once_with(
        [projects_tabs, funding_tabs, budget_tabs, funder_tabs],
        ncols=2,
        sizing_mode="stretch_width",
    )
    column_mock.assert_called_once_with([gridplot], sizing_mode="stretch_width")
    assert layout_actual == layout_expected


def test_create_allocation_plot_for_project_with_zero_allocations(phase):
    """A project with a date range but zero allocations still gets a plot.

    Only the "Project FTE" line should be present, per #860.
    """
    from bokeh.plotting import figure

    from main import plots

    project = phase.project
    assert not project.allocation_set.exists()

    plot = plots.create_allocation_plot_for_project(project, x_range=None)

    assert isinstance(plot, figure)
    legend_items = [item.label.value for item in plot.legend.items]
    assert legend_items == ["Project FTE"]


def test_create_allocation_plot_for_project_with_allocations(phase, user):
    """A project with allocations gets one line per user.

    Expect one line per user, plus the total allocation and the project FTE lines.
    """
    from bokeh.plotting import figure

    from main import models, plots

    project = phase.project
    models.Allocation.objects.create(
        project=project,
        user=user,
        start_date=project.start_date,
        end_date=project.end_date,
        value=0.5,
    )

    plot = plots.create_allocation_plot_for_project(project, x_range=None)

    assert isinstance(plot, figure)
    legend_items = [item.label.value for item in plot.legend.items]
    assert "Project FTE" in legend_items
    assert str(user) in legend_items
    assert "Allocated FTE" in legend_items


def test_create_allocation_plot_for_project_without_dates(user, department):
    """A project with no date range (e.g. Tentative) gets no plot at all."""
    from main import models, plots

    project = models.Project.objects.create(
        name="Tentative project",
        department=department,
        lead=user,
        status="Tentative",
        start_date=None,
        end_date=None,
    )

    assert plots.create_allocation_plot_for_project(project, x_range=None) is None
