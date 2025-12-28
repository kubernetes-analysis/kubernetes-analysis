from typing import Any

from .cli import Cli
from .data import Data
from .nlp import TuneParams


class Train(Cli):
    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(command,
                                       help="train the machine learning model")
        parser.add_argument("--tune",
                            "-t",
                            action="store_true",
                            help="Tune the hyper parameters")
        parser.add_argument("--label",
                            "-l",
                            type=str,
                            default="kind/bug",
                            help="The label to classify (default: 'kind/bug')")
        parser.add_argument("--layers",
                            "-a",
                            type=int,
                            default=2,
                            help="The number of layers used for each tuning run (default: 2)")
        parser.add_argument("--units",
                            "-u",
                            type=int,
                            default=64,
                            help="The number of units used for each tuning run (default: 8)")

    def run(self):
        Data().train_release_notes_by_label(self.args.label, self.args.tune,
                                            TuneParams(self.args.layers, self.args.units))
