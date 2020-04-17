import json
import logging
import os
import re
import tarfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .bag_of_words import BagOfWords
from .issue import Issue
from .label import Label
from .pull_request import PullRequest
from .series import Series

DATA_DIR = "data"

API_JSON = "api.json"
API_DATA_JSON = os.path.join(DATA_DIR, API_JSON)
API_DATA_TARBALL = os.path.join(DATA_DIR, "api.tar.xz")

BOW_JSON = "bow.json"
BOW_DATA_JSON = os.path.join(DATA_DIR, BOW_JSON)
BOW_DATA_TARBALL = os.path.join(DATA_DIR, "bow.tar.xz")


class Filter(Enum):
    ALL = 1
    ISSUES = 2
    PULL_REQUESTS = 3


class Data():
    # Dict indexed by their ID
    __issues: Dict[int, Issue]
    __pull_requests: Dict[int, PullRequest]

    __filter: Filter
    __parse_nlp: bool

    __api_json: List[Any]
    __bow_json: Optional[List[Dict]]

    __include_regex: Optional[str]
    __exclude_regex: Optional[str]

    BOW_ALL_KEY = "all"
    BOW_RELEASE_NOTES_KEY = "release_notes"

    def __init__(self, parse_nlp=False):
        Data.__extract_api_data()

        logging.info("Enabled NLP from raw data: %s", parse_nlp)
        self.__bow_json = None
        self.__parse_nlp = parse_nlp

        api_data_file = open(API_DATA_JSON, "r")
        logging.info("Loading API JSON content")
        self.__api_json = json.load(api_data_file)
        self.__init_api_json()

        if not parse_nlp:
            Data.__extract_bow_data()

            logging.info("Loading bag of words JSON content")
            bow_data_file = open(BOW_DATA_JSON, "r")
            self.__bow_json = json.load(bow_data_file)
            self.__init_bow_json()

        self.__filter = Filter.ALL
        self.__include_regex = None
        self.__exclude_regex = None

    def __init_api_json(self):
        logging.info("Parsing API JSON content")
        self.__issues = {}
        self.__pull_requests = {}

        pool_count = os.cpu_count()
        with ThreadPoolExecutor(max_workers=pool_count) as e:
            pr_key = "pull_request"
            futures = []

            logging.info("Adding pull requests to thread pool")
            for x in [x for x in self.__api_json if pr_key in x.keys()]:
                futures.append(e.submit(self.__append_pull_request, x))

            logging.info("Adding issues to thread pool")
            for x in [x for x in self.__api_json if pr_key not in x.keys()]:
                futures.append(e.submit(self.__append_issue, x))

            logging.info("Waiting for executor for finish")
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.critical("Parsing failed: %s", e)

        logging.info("Parsed %d issues and %d pull requests (%d items)",
                     len(self.__issues), len(self.__pull_requests),
                     len(self.__issues) + len(self.__pull_requests))

    def __append_pull_request(self, item: Dict):
        pr = PullRequest(item, self.__parse_nlp)
        self.__pull_requests[pr.id] = pr

    def __append_issue(self, item: Dict):
        issue = Issue(item, self.__parse_nlp)
        self.__issues[issue.id] = issue

    def __init_bow_json(self):
        logging.info("Parsing bag of words JSON content")

        for item_id, item in self.__bow_json.items():
            i = int(item_id)

            # Issues are just stored as lists
            if isinstance(item, list) and i in self.__issues:
                self.__issues[i].bag_of_words = BagOfWords(words=item)

            # PRs are stored as dictionaries
            elif i in self.__pull_requests:
                if item[Data.BOW_ALL_KEY]:
                    bow = BagOfWords(words=item[Data.BOW_ALL_KEY])
                    self.__pull_requests[i].bag_of_words = bow

                if item[Data.BOW_RELEASE_NOTES_KEY]:
                    bow = BagOfWords(words=item[Data.BOW_RELEASE_NOTES_KEY])
                    self.__pull_requests[i].release_note_bag_of_words = bow

        logging.info("Parsed %d bag of word items", len(self.__bow_json))

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
    def api_to_tarball():
        logging.info("Compressing API data")
        with tarfile.open(API_DATA_TARBALL, "w:xz") as tar:
            tar.add(API_DATA_JSON, API_JSON)

    @staticmethod
    def __extract_api_data():
        Data.__extract(API_DATA_TARBALL, API_DATA_JSON)

    @staticmethod
    def __extract_bow_data():
        Data.__extract(BOW_DATA_TARBALL, BOW_DATA_JSON)

    @staticmethod
    def __extract(tarball: str, target_file: str):
        if os.path.isfile(target_file):
            logging.info("Using already extracted data")
        else:
            logging.info("Extracting API data")
            tarfile.open(tarball).extractall(path=DATA_DIR)

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
        with open(API_DATA_JSON, "w") as outfile:
            json.dump(self.__api_json, outfile)

    def dump_bag_of_words(self):
        res = {}

        for issue in self.__issues.values():
            if issue.bag_of_words:
                res[issue.id] = issue.bag_of_words.words

        for pr in self.__pull_requests.values():
            if pr.bag_of_words:
                res[pr.id] = {
                    Data.BOW_ALL_KEY: pr.bag_of_words.words,
                }
                if pr.release_note_bag_of_words:
                    words = pr.release_note_bag_of_words.words
                    res[pr.id][Data.BOW_RELEASE_NOTES_KEY] = words

        with open(BOW_DATA_JSON, "w") as outfile:
            json.dump(res, outfile)

        logging.info("Compressing bag of words data")
        with tarfile.open(BOW_DATA_TARBALL, "w:xz") as tar:
            tar.add(BOW_DATA_JSON, BOW_JSON)

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
            return list(self.__issues.values())

        if self.filter == Filter.PULL_REQUESTS:
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
