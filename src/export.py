import datetime
import json
import os
import sys
import time
from typing import Any, Optional, Tuple

from github import Github, Repository
from loguru import logger

from .cli import Cli
from .data import Data


class Export(Cli):
    GITHUB_TOKEN = "GITHUB_TOKEN"
    API_UPDATE_FILE = ".update"

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(
            command, help="export data from the GitHub API or prepare it")

        update_group = parser.add_mutually_exclusive_group()

        update_group.add_argument("--update-api",
                                  "-u",
                                  action="store_true",
                                  help="Update the API json")

        update_group.add_argument("--update-data",
                                  "-d",
                                  action="store_true",
                                  help="Update the data set")

    def run(self):
        if self.args.update_data:
            logger.info("Updating local data")
            Data(parse=True).dump()
            return

        token = Export.get_github_token()
        github = Github(token)
        repo = github.get_repo("kubernetes/kubernetes")

        if self.args.update_api:
            logger.info("Retrieving issues and PRs")

            logger.info("Updating API")
            Export.update_api(repo)

        else:
            logger.info("Dumping all issues")
            Export.dump_api(repo)

    @staticmethod
    def get_github_token() -> Optional[str]:
        logger.info("Getting {} from environment variable",
                    Export.GITHUB_TOKEN)
        token = os.environ.get(Export.GITHUB_TOKEN)
        if token is None:
            logger.critical("{} environment variable not set",
                            Export.GITHUB_TOKEN)
            sys.exit(1)
        return token

    @staticmethod
    def dump_api(repo: Repository):
        result = []

        # We use the first (latest) issue as indicator of how many data we have
        # to fetch
        issues = repo.get_issues(state="all")
        latest_issue = issues[0]
        count = latest_issue.number
        logger.info("Pulling {} items", count)

        for i in range(1, count + 1):
            try:
                issue = repo.get_issue(i)
                logger.info("{}: {}", issue.number, issue.title)
                result.append(issue.raw_data)
            except Exception as err:
                logger.info("Unable to get data, waiting a minute: {}", err)
                time.sleep(60)

        with open(Data.API_DATA_JSON, "w") as data_file:
            json.dump(result, data_file)

        logger.info("Done exporting {} items", i)
        Data.api_to_tarball()

    @staticmethod
    def update_api(repo: Repository):
        (update_file,
         date) = Export.get_update_file_date(Export.API_UPDATE_FILE)

        json_list = []
        for issue in repo.get_issues(
                since=date,
                sort="updated",
                state="all",
        ):
            logger.info("{}: {}", issue.number, issue.title)
            json_list.append(issue.raw_data)

        data = Data()

        logger.info("Updating data")
        data.update_api_data(json_list)

        logger.info("Saving data")
        data.dump_api()

        Data.api_to_tarball()
        Export.write_update_file_date(update_file)

    @staticmethod
    def get_update_file_date(file_name: str) -> Tuple[Any, Any]:
        # load the update file contents
        update_file = open(file_name, "r+")
        date = datetime.datetime.strptime(update_file.read().strip(),
                                          "%Y-%m-%dT%H:%M:%S.%f")
        logger.info("Got update timestamp: {}", date.isoformat())
        return (update_file, date)

    @staticmethod
    def write_update_file_date(update_file: Any):
        # update the file
        update_file.seek(0, 0)
        new_date = datetime.datetime.utcnow().isoformat()
        logger.info("New update timestamp: {}", new_date)
        update_file.write(new_date)
