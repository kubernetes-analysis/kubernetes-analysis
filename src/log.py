import logging as log
import sys


class ShutdownHandler(log.Handler):
    def emit(self, record):
        log.shutdown()
        sys.exit(1)


def setup(level):
    logger = log.getLogger()
    logger.setLevel(level)

    formatter = log.Formatter("[%(asctime)s] [%(levelname)8s]: %(message)s",
                              "%Y-%m-%d %H:%M:%S")

    ch = log.StreamHandler()
    ch.setLevel(log.DEBUG)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(ShutdownHandler(level=50))
