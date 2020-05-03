from typing import Any

import kfserving

from .cli import Cli
from .kfserver import KFServer


class Serve(Cli):
    SERVICE_NAME = "kubernetes-analysis"

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        subparsers.add_parser(command, help="serve the machine learning model")

    @staticmethod
    def run():
        model = KFServer(Serve.SERVICE_NAME)
        model.load()
        kfserving.KFServer(workers=1).start([model])
