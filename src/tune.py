from typing import Any

from .cli import Cli
from .data import Data
from .nlp import DEFAULT_PARAMS, TuneParams


class Tune(Cli):
    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(command,
                                       help="tune the machine learning model")
        parser.add_argument("--label",
                            "-l",
                            type=str,
                            default="kind/bug",
                            help="The label to classify (default: 'kind/bug')")
        parser.add_argument("--layers",
                            "-a",
                            type=int, nargs="+",
                            default=DEFAULT_PARAMS.layers,
                            help="The number of layers used for each tuning run \
                                    (default: %s)" % DEFAULT_PARAMS.layers)
        parser.add_argument("--units",
                            "-u",
                            type=int, nargs="+",
                            default=DEFAULT_PARAMS.layers,
                            help="The number of units used for each tuning run \
                                    (default: %s)" % DEFAULT_PARAMS.units)

    def run(self):
        params = TuneParams(self.args.layers, self.args.units)
        Data().train_release_notes_by_label(self.args.label, True, params)
