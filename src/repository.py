import os
import sys

from git import Repo
from loguru import logger


class Repository():
    __repo: Repo

    def __init__(self):
        logger.info("Opening repository at current working path")
        self.__repo = Repo(os.getcwd())

    def checkout(self, revision: str):
        logger.info("Pulling from remote origin")
        self.__repo.remote().pull()

        logger.info("Checking out revision {}", revision)
        try:
            self.__repo.git.checkout(revision)
        except Exception as e:
            logger.error("Unable to checkout {}: {}", revision, e)
            sys.exit(1)
