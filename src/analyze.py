from typing import Any

from loguru import logger

from .cli import Cli
from .data import Data, Filter
from .plot import Plot


class Analyze(Cli):
    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(command, help="analyze the data")

        parser.add_argument("--no-plot-gtk",
                            "-n",
                            action="store_true",
                            help="Do not plot as GTK window")

        parser.add_argument("--save-svg",
                            "-s",
                            type=str,
                            metavar="FILE",
                            help="Save the plot as SVG file")

        parser.add_argument(
            "--include",
            "-l",
            type=str,
            metavar="FILTER",
            help="Include labels or users by the provided regex")

        parser.add_argument(
            "--exclude",
            "-e",
            type=str,
            metavar="FILTER",
            help="Exclude labels or users by the provided regex")

        parser.add_argument("--count",
                            "-c",
                            type=int,
                            metavar="COUNT",
                            default=25,
                            help="Display only the specified amount of labels")

        parser.add_argument("--parse",
                            "-r",
                            action="store_true",
                            help="Parse data live instead of restoring")

        select_group = parser.add_mutually_exclusive_group()
        select_group.add_argument("--created",
                                  "-1",
                                  action="store_true",
                                  help="show created issues/PRs over time")

        select_group.add_argument("--closed",
                                  "-2",
                                  action="store_true",
                                  help="show closed issues/PRs over time")

        select_group.add_argument(
            "--created-vs-closed",
            "-3",
            action="store_true",
            help="show created vs closed issues/PRs over time")

        select_group.add_argument("--labels-by-name",
                                  "-4",
                                  action="store_true",
                                  help="show use labels by name")

        select_group.add_argument("--labels-by-group",
                                  "-5",
                                  action="store_true",
                                  help="show used labels by group")

        select_group.add_argument("--users-by-created",
                                  "-6",
                                  action="store_true",
                                  help="show users by created issues/PRs")

        select_group.add_argument("--users-by-closed",
                                  "-7",
                                  action="store_true",
                                  help="show users by closed issues/PRs")

        select_group.add_argument("--release-notes-stats",
                                  "-8",
                                  action="store_true",
                                  help="show release notes stats for PRs")

        filter_group = parser.add_mutually_exclusive_group()
        filter_group.add_argument("--pull-requests",
                                  "-p",
                                  action="store_true",
                                  help="filter PRs only")

        filter_group.add_argument("--issues",
                                  "-i",
                                  action="store_true",
                                  help="filter issues only")

    def run(self):
        Plot.init()

        filter_text = "issues and PRs"
        fil = Filter.ALL
        if self.args.pull_requests:
            logger.info("Filtering pull requests only")
            filter_text = "PRs"
            fil = Filter.PULL_REQUESTS

        if self.args.issues:
            logger.info("Filtering issues only")
            filter_text = "issues"
            fil = Filter.ISSUES

        # Parse the data
        data = Data(parse=self.args.parse, filter_value=fil)

        # Created over time
        if self.args.created:
            plot = Plot(data.created_time_series())
            x = plot.time("Created %s over time" % filter_text)
            plot.annotate_chunked(x)

        # Closed over time
        if self.args.closed:
            plot = Plot(data.closed_time_series())
            x = plot.time("Closed %s over time" % filter_text)
            plot.annotate_chunked(x)

        # Created vs Closed over time
        if self.args.created_vs_closed:
            plot = Plot(data.created_vs_closed_time_series())
            x = plot.time("Created vs closed %s over time" % filter_text)
            plot.annotate_chunked(x)

        if self.args.labels_by_name or self.args.labels_by_group or (
                self.args.users_by_created or self.args.users_by_closed):
            data.include_regex = self.args.include
            data.exclude_regex = self.args.exclude

        # Label usage by name
        if self.args.labels_by_name:
            series = data.label_name_usage_series()
            plot = Plot(series)
            logger.info("Got {} distinct labels and {} results", len(series),
                        sum(series))
            logger.debug("Results:\n{}", series)
            plot.barh("Label usage by name for %s" % filter_text,
                      self.args.count)

        # Label usage by name
        if self.args.labels_by_group:
            series = data.label_group_usage_series()
            plot = Plot(series)
            logger.info("Got {} distinct label groups and {} results",
                        len(series), sum(series))
            logger.debug("Results:\n{}", series)
            plot.barh("Label usage by label group for %s" % filter_text,
                      self.args.count)

        # Created by user
        if self.args.users_by_created:
            series = data.user_created_series()
            plot = Plot(series)
            logger.info("Got {} distinct users and {} results", len(series),
                        sum(series))
            logger.debug("Results:\n{}", series)
            plot.barh("Created by user for %s" % filter_text, self.args.count)

        # Closed by user
        if self.args.users_by_closed:
            series = data.user_closed_series()
            plot = Plot(series)
            logger.info("Got {} distinct users and {} results", len(series),
                        sum(series))
            logger.debug("Results:\n{}", series)
            plot.barh("Closed by user for %s" % filter_text, self.args.count)

        # Release notes statistics
        if self.args.release_notes_stats:
            data.release_notes_stats()
            return

        if self.args.save_svg:
            Plot.save(self.args.save_svg)
            return

        if not self.args.no_plot_gtk:
            Plot.show()
