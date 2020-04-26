from argparse import Namespace
from typing import Any

from .data import Data


class Train():
    __args: Namespace

    def __init__(self, args: Namespace):
        self.__args = args

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
        Data().train_release_notes_by_label(self.__args.label,
                                            self.__args.tune)
