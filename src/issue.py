from datetime import datetime
from typing import Dict, Optional

import markdown2
from bs4 import BeautifulSoup
from bs4.element import Comment

from .bag_of_words import BagOfWords
from .label import Labels


class Issue():
    __id: int
    __title: str
    __url: str
    __number: int
    __created: datetime
    __closed: Optional[datetime]
    __labels: Labels
    __bag_of_words: Optional[BagOfWords]
    __markdown: Optional[str]

    def __init__(self, data: Dict, parse_nlp=False):
        self.__id = data["id"]
        self.__title = data["title"]
        self.__url = data["html_url"]
        self.__number = data["number"]
        self.__markdown = data["body"]
        self.__bag_of_words = None

        if parse_nlp:
            self.__bag_of_words = Issue.__parse_bag_of_words(data["body"])

        fmt = "%Y-%m-%dT%H:%M:%S%z"
        self.__created = datetime.strptime(data["created_at"], fmt)

        if data["closed_at"] is not None:
            self.__closed = datetime.strptime(data["closed_at"], fmt)
        else:
            self.__closed = None

        self.__labels = Labels(data["labels"])

    @staticmethod
    def __parse_bag_of_words(markdown: Optional[str]) -> Optional[BagOfWords]:
        if not markdown:
            return None

        plain_text = Issue.__markdown_to_text(markdown)
        if not plain_text:
            return None

        return BagOfWords(text=plain_text)

    @staticmethod
    def __markdown_to_text(markdown: str) -> str:
        html = markdown2.markdown(markdown)
        soup = BeautifulSoup(html, "html.parser")
        text_elements = soup.findAll(text=True)
        visible_texts = filter(Issue.__element_is_visible, text_elements)

        return u" ".join(t.strip() for t in visible_texts)

    @staticmethod
    def __element_is_visible(element) -> bool:
        if element.parent.name in [
                "style", "script", "head", "title", "meta", "[document]"
        ] or isinstance(element, Comment):
            return False
        return True

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
    def bag_of_words(self) -> Optional[BagOfWords]:
        return self.__bag_of_words

    @bag_of_words.setter
    def bag_of_words(self, value: BagOfWords):
        self.__bag_of_words = value

    @property
    def markdown(self) -> Optional[str]:
        return self.__markdown
