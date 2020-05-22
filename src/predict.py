import sys
from typing import Any

from loguru import logger

from .cli import Cli
from .nlp import Nlp


class Predict(Cli):
    # From: https://github.com/kubernetes/kubernetes/pull/65327
    POSITIVE_TEST_TEXT = """
        Fix concurrent map access panic
        Don't watch .mount cgroups to reduce number of inotify watches
        Fix NVML initialization race condition
        Fix brtfs disk metrics when using a subdirectory of a subvolume
    """

    # From: https://github.com/kubernetes/kubernetes/pull/85363
    NEGATIVE_TEST_TEXT = """
        action required
        1. Currently, if users were to explicitly specify CacheSize of 0 for
           KMS provider, they would end-up with a provider that caches up to
           1000 keys. This PR changes this behavior.
           Post this PR, when users supply 0 for CacheSize this will result in
           a validation error.
        2. CacheSize type was changed from int32 to *int32. This allows
           defaulting logic to differentiate between cases where users
           explicitly supplied 0 vs. not supplied any value.
        3. KMS Provider's endpoint (path to Unix socket) is now validated when
           the EncryptionConfiguration files is loaded. This used to be handled
           by the GRPCService.
    """

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(
            command, help="predict text for the trained model")

        parser.add_argument("text",
                            type=str,
                            default="",
                            nargs="?",
                            help="The text to predict")

        parser.add_argument(
            "--threshold",
            "-r",
            default=.6,
            type=float,
            help="The threshold for returning a positive exit code")

        parser.add_argument("--test",
                            "-t",
                            action="store_true",
                            help="Run two simple test cases")

    def run(self):
        if self.args.test:
            logger.info("Testing positive text:\n{}",
                        Predict.POSITIVE_TEST_TEXT)
            self.predict_and_evaluate(Predict.POSITIVE_TEST_TEXT)

            logger.info("Testing negative text:\n{}",
                        Predict.NEGATIVE_TEST_TEXT)
            self.predict_and_evaluate(Predict.NEGATIVE_TEST_TEXT,
                                      expected_positive=False)

        else:
            self.predict_and_evaluate(self.args.text)

    def predict_and_evaluate(self, text: str, expected_positive: bool = True):
        result = Nlp.predict(text)
        logger.info("Got prediction result: {}", result)

        if expected_positive and result < self.args.threshold:
            logger.error("Result is lower than selected threshold {}",
                         self.args.threshold)
            sys.exit(1)

        logger.info("Matched expected {} prediction result",
                    "positive" if expected_positive else "negative")
