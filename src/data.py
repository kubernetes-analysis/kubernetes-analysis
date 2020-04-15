import json
import logging
import os
import re
import tarfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .issue import Issue
from .label import Label
from .pull_request import PullRequest
from .series import Series

DATA_JSON = "data.json"
DATA_TARBALL = "data.tar.xz"


class Filter(Enum):
    ALL = 1
    ISSUES = 2
    PULL_REQUESTS = 3


class Data():
    __issues: List[Issue]
    __pull_requests: List[PullRequest]
    __filter: Filter
    __json: List[Any]
    __enable_nlp: bool
    __include_regex: Optional[str]
    __exclude_regex: Optional[str]

    def __init__(self, enable_nlp=False):
        logging.info("NLP support: %s", enable_nlp)

        Data.__extract()

        self.__filter = Filter.ALL
        self.__include_regex = None
        self.__exclude_regex = None
        self.__enable_nlp = enable_nlp

        data_file = open(DATA_JSON, "r")

        logging.info("Loading JSON content")
        self.__json = json.load(data_file)

        self.__init_json()

    def __init_json(self):
        logging.info("Parsing JSON content")
        self.__issues = []
        self.__pull_requests = []

        pool_count = os.cpu_count()
        with ThreadPoolExecutor(max_workers=pool_count) as e:
            pr_key = "pull_request"

            logging.info("Adding pull requests to thread pool")
            e.map(self.__append_pull_request,
                  [x for x in self.__json if pr_key in x.keys()])

            logging.info("Adding issues to thread pool")
            e.map(self.__append_issue,
                  [x for x in self.__json if pr_key not in x.keys()])

            logging.info("Waiting for executor for finish")

        logging.info("Parsed %d issues and %d pull requests (%d items)",
                     len(self.__issues), len(self.__pull_requests),
                     len(self.__issues) + len(self.__pull_requests))

    def __append_pull_request(self, item: Dict):
        self.__pull_requests.append(PullRequest(item, self.__enable_nlp))

    def __append_issue(self, item: Dict):
        self.__issues.append(Issue(item, self.__enable_nlp))

    @property
    def filter(self) -> Filter:
        return self.__filter

    @filter.setter
    def filter(self, filter_value: Filter):
        self.__filter = filter_value

    @property
    def include_regex(self) -> Optional[str]:
        return self.__include_regex

    @include_regex.setter
    def include_regex(self, regex: Optional[str]):
        if regex:
            self.__include_regex = re.compile(regex)

    @property
    def exclude_regex(self) -> Optional[str]:
        return self.__exclude_regex

    @exclude_regex.setter
    def exclude_regex(self, regex: Optional[str]):
        if regex:
            self.__exclude_regex = re.compile(regex)

    @staticmethod
    def to_tarball():
        logging.info("Compressing data")
        with tarfile.open(DATA_TARBALL, "w:xz") as tar:
            tar.add(DATA_JSON)

    @staticmethod
    def __extract():
        if not os.path.isfile(DATA_JSON):
            logging.info("Extracting data")
            tarfile.open(DATA_TARBALL).extractall()
        else:
            logging.info("Using already extracted data")

    def update(self, json_data: List[Dict]):
        new_issues = []

        for json_issue in json_data:
            found = False

            for idx, item in enumerate(self.__json):
                if item["id"] == json_issue["id"]:
                    logging.info("Updating issue %d (updated at %s)",
                                 json_issue["number"],
                                 json_issue["updated_at"])
                    self.__json[idx] = json_issue
                    found = True

            if not found:
                new_issues.append(json_issue)

        for new_issue in new_issues:
            logging.info("Adding new issue %d", new_issue["number"])
            self.__json.append(new_issue)

        self.__init_json()

    def dump(self):
        with open(DATA_JSON, "w") as outfile:
            json.dump(self.__json, outfile)

    def created_time_series(self) -> Series:
        return self.__time_series(lambda issue: issue.created)

    def closed_time_series(self) -> Series:
        return self.__time_series(lambda issue: issue.closed)

    def created_vs_closed_time_series(self) -> Series:
        events: List[Tuple[datetime, int]] = []

        for item in self.__items():
            events.append((item.created, 1))
            if item.closed is not None:
                events.append((item.closed, -1))

        sorted_events = sorted(events, key=lambda event: event[0])
        series = Series()
        count = 0
        for event in sorted_events:
            count += event[1]
            series.add(event[0], count)
        return series

    def label_name_usage_series(self) -> Series:
        return self.__label_series(
            lambda label: self.__filter_regex(label.name))

    def label_group_usage_series(self) -> Series:
        return self.__label_series(
            lambda label: self.__filter_regex(label.group))

    def __filter_regex(
            self,
            string: Optional[str],
    ) -> Optional[str]:
        if not string:
            return None

        # no filter applied at all
        if not self.include_regex and not self.exclude_regex:
            return string

        # include only
        if self.include_regex and not self.exclude_regex:
            if self.include_regex.search(string):
                return string
            return None

        # exclude only
        if self.exclude_regex and not self.include_regex:
            if self.exclude_regex.search(string):
                return None
            return string

        # include and exclude
        if self.include_regex.search(
                string) and not self.exclude_regex.search(string):
            return string

        return None

    def __items(self) -> List[Issue]:
        if self.filter == Filter.ISSUES:
            return self.__issues

        if self.filter == Filter.PULL_REQUESTS:
            return self.__pull_requests

        return self.__issues + self.__pull_requests

    def __time_series(self, fun: Callable[[Issue],
                                          Optional[datetime]]) -> Series:
        series = Series()

        items = sorted(filter(lambda x: fun(x) is not None, self.__items()),
                       key=fun)
        count = 0
        for item in items:
            count += 1
            series.add(fun(item), count)

        return series

    def __label_series(self, fun: Callable[[Label], Optional[str]]) -> Series:
        series = Series()
        for label, issues in self.__grouped_by_labels(fun):
            series.add(fun(label), len(issues))
        return series

    def __grouped_by_labels(
        self, fun: Callable[[Label], Optional[str]]
    ) -> List[Tuple[Label, List[Issue]]]:
        res: Dict[str, Tuple[Label, List[Issue]]] = {}
        for item in self.__items():
            for label in item.labels:
                key = fun(label)
                if key is None:
                    continue
                if key in res:
                    res[key][1].append(item)
                else:
                    res[key] = (label, [item])
        return sorted(res.values(), key=lambda x: len(x[1]))
