from typing import Any

from .cli import Cli
from .data import Data


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

    def run(self):
        Data().train_release_notes_by_label(self.args.label, self.args.tune)
