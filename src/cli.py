from argparse import Namespace


class Cli():
    __args: Namespace

    def __init__(self, args: Namespace):
        self.__args = args

    @property
    def args(self) -> Namespace:
        return self.__args
