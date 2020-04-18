import json
import logging
import os
import pickle
import re
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .issue import Issue
from .label import Label
from .pull_request import PullRequest
from .series import Series


class Filter(Enum):
    ALL = 1
    ISSUES = 2
    PULL_REQUESTS = 3


class Data():
    # Dict indexed by their ID
    __issues: Dict[int, Issue]
    __pull_requests: Dict[int, PullRequest]

    __filter: Filter
    __parse: bool

    __api_json: Optional[List[Any]]

    __include_regex: Optional[str]
    __exclude_regex: Optional[str]

    __now: float

    DATA_DIR = "data"

    API_JSON = "api.json"
    API_DATA_JSON = os.path.join(DATA_DIR, API_JSON)
    API_DATA_TARBALL = os.path.join(DATA_DIR, "api.tar.xz")

    FILE = "data.pickle"
    PATH = os.path.join(DATA_DIR, FILE)
    TARBALL = os.path.join(DATA_DIR, "data.tar.xz")

    BOW_ALL_KEY = "all"
    BOW_RELEASE_NOTES_KEY = "release_notes"
    PR_KEY = "pull_request"

    def __init__(self, parse=False, filter_value=Filter.ALL):
        if not parse:
            Data.__extract_data()
            self.__dict__.update(pickle.load(open(Data.PATH, "rb")))
            return

        self.__parse = parse
        self.__filter = filter_value
        self.__include_regex = None
        self.__exclude_regex = None

        logging.info("Parsing data")
        Data.__extract_api_data()

        api_data_file = open(Data.API_DATA_JSON, "r")
        logging.info("Loading API JSON file")
        self.__api_json = json.load(api_data_file)
        self.__init_api_json()

    def __init_api_json(self):
        logging.info("Parsing API JSON content")
        self.__issues = {}
        self.__pull_requests = {}

        pool_count = os.cpu_count()
        executor = ThreadPoolExecutor(max_workers=pool_count)
        self.__now = time.process_time()

        futures = []
        logging.info("Adding work items to thread pool")
        for i, item in enumerate(self.__api_json):
            futures.append(executor.submit(self.__parse_api_item, item, i))

        logging.info("Waiting for executor for finish")
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.critical("Parsing failed: %s", e)

        logging.info("Parsed %d issues and %d pull requests (%d items)",
                     len(self.__issues), len(self.__pull_requests),
                     len(self.__issues) + len(self.__pull_requests))

    def __parse_api_item(self, item: Dict, i: int):
        if time.process_time() - self.__now > 10:
            logging.info("%.1f%% (%d / %d) [%d PRs / %d issues]",
                         i / len(self.__api_json) * 100, i,
                         len(self.__api_json), len(self.__pull_requests),
                         len(self.__issues))
            self.__now = time.process_time()

        if self.__filter != Filter.ISSUES and Data.PR_KEY in item:
            pr = PullRequest(item, self.__parse)
            self.__pull_requests[pr.id] = pr

        elif self.__filter != Filter.PULL_REQUESTS:
            issue = Issue(item, self.__parse)
            self.__issues[issue.id] = issue

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
    def api_to_tarball():
        logging.info("Compressing API data")
        with tarfile.open(Data.API_DATA_TARBALL, "w:xz") as tar:
            tar.add(Data.API_DATA_JSON, Data.API_JSON)

    @staticmethod
    def __extract_api_data():
        Data.__extract(Data.API_DATA_TARBALL, Data.API_DATA_JSON)

    @staticmethod
    def __extract_data():
        Data.__extract(Data.TARBALL, Data.PATH)

    @staticmethod
    def __extract(tarball: str, target_file: str):
        if os.path.isfile(target_file):
            logging.info("Using already extracted data from %s", target_file)
        else:
            logging.info("Extracting API data")
            tarfile.open(tarball).extractall(path=Data.DATA_DIR)

    def update_api_data(self, json_data: List[Dict]):
        new_issues = []

        for json_issue in json_data:
            found = False

            for idx, item in enumerate(self.__api_json):
                if item["id"] == json_issue["id"]:
                    logging.info("Updating issue %d (updated at %s)",
                                 json_issue["number"],
                                 json_issue["updated_at"])
                    self.__api_json[idx] = json_issue
                    found = True

            if not found:
                new_issues.append(json_issue)

        for new_issue in new_issues:
            logging.info("Adding new issue %d", new_issue["number"])
            self.__api_json.append(new_issue)

        self.__init_api_json()

    def dump_api(self):
        with open(Data.API_DATA_JSON, "w") as outfile:
            json.dump(self.__api_json, outfile)

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
        if self.__filter == Filter.ISSUES:
            return list(self.__issues.values())

        if self.__filter == Filter.PULL_REQUESTS:
            return list(self.__pull_requests.values())

        return list(self.__issues.values()) + list(
            self.__pull_requests.values())

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

    def user_created_series(self) -> Series:
        return self.__user_series(
            lambda issue: self.__filter_regex(issue.created_by))

    def user_closed_series(self) -> Series:
        return self.__user_series(
            lambda issue: self.__filter_regex(issue.closed_by))

    def __user_series(self, fun: Callable[[Issue], Optional[str]]) -> Series:
        series = Series()
        for issue, issues in self.__grouped_by_users(fun):
            series.add(fun(issue), len(issues))
        return series

    def __grouped_by_users(
        self, fun: Callable[[Issue], Optional[str]]
    ) -> List[Tuple[Issue, List[Issue]]]:
        res: Dict[str, Tuple[Issue, List[Issue]]] = {}
        for item in self.__items():
            user = fun(item)
            if user is None:
                continue
            if user in res:
                res[user][1].append(item)
            else:
                res[user] = (item, [item])
        return sorted(res.values(), key=lambda x: len(x[1]))

    def dump(self):
        logging.info("Saving data to %s", Data.PATH)
        with open(Data.PATH, "wb") as outfile:
            pickle.dump(self.__dict__, outfile)

        logging.info("Compressing data to %s", Data.TARBALL)
        with tarfile.open(Data.TARBALL, "w:xz") as tar:
            tar.add(Data.PATH, Data.FILE)
