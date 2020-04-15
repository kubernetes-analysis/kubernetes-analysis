from typing import Any, List

import numpy as np


class Series():
    __xs: List
    __ys: List

    def __init__(self):
        self.__xs = []
        self.__ys = []

    def add(self, x_val: Any, y_val: Any):
        self.__xs.append(x_val)
        self.__ys.append(y_val)

    def zip(self) -> List:
        return [list(a) for a in zip(self.__xs, self.__ys)]

    def chunk(self, chunks: int) -> List[List]:
        return np.array_split(self.zip(), chunks)

    @property
    def x(self) -> List:
        return self.__xs

    @property
    def y(self) -> List:
        return self.__ys

    def __str__(self) -> str:
        res = ""
        for i, val in enumerate(self.__xs):
            res += "%s : %s\n" % (val, self.__ys[i])
        return res

    def __len__(self) -> int:
        return len(self.__xs)

    def __iter__(self):
        return self.__ys.__iter__()

    def __next__(self):
        return next(self.__ys)
