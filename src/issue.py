from datetime import datetime
from typing import Dict, Optional

from .label import Labels


class Issue():
    __id: int
    __title: str
    __url: str
    __number: int

    __created: datetime
    __closed: Optional[datetime]

    __created_by: str
    __closed_by: Optional[str]

    __labels: Labels
    __markdown: Optional[str]

    def __init__(self, data: Dict):
        self.__id = data["id"]
        self.__title = data["title"]
        self.__url = data["html_url"]
        self.__number = data["number"]
        self.__markdown = data["body"]

        fmt = "%Y-%m-%dT%H:%M:%SZ"
        self.__created = datetime.strptime(data["created_at"], fmt)

        if data["closed_at"] is not None:
            self.__closed = datetime.strptime(data["closed_at"], fmt)
        else:
            self.__closed = None

        self.__created_by = data["user"]["login"]
        self.__closed_by = None
        if data["closed_by"]:
            self.__closed_by = data["closed_by"]["login"]

        self.__labels = Labels(data["labels"])

    @property
    def id(self) -> int:
        return self.__id

    @property
    def title(self) -> str:
        return self.__title

    @property
    def labels(self) -> Labels:
        return self.__labels

    @property
    def created(self) -> Optional[datetime]:
        return self.__created

    @property
    def closed(self) -> Optional[datetime]:
        return self.__closed

    @property
    def url(self) -> str:
        return self.__url

    @property
    def number(self) -> int:
        return self.__number

    @property
    def markdown(self) -> Optional[str]:
        return self.__markdown

    @property
    def created_by(self) -> str:
        return self.__created_by

    @property
    def closed_by(self) -> Optional[str]:
        return self.__closed_by
