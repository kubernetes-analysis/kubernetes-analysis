from typing import Dict, List, Optional


class Label():
    __name: str
    __group: Optional[str]

    def __init__(self, data: Dict):
        self.__name = data["name"]
        self.__group = None
        split = self.__name.split("/", 1)
        if len(split) > 1:
            self.__group = split[0]

    @property
    def name(self) -> str:
        return self.__name

    @property
    def group(self) -> str:
        return self.__group


class Labels():
    __labels: List[Label] = []

    def __init__(self, data: Dict):
        self.__labels = []
        for item in data:
            self.__labels.append(Label(item))

    def __iter__(self):
        return self.__labels.__iter__()

    def __next__(self):
        return next(self.__labels)
