from typing import Any

from kfserving import (KFServingClient, V1alpha2CustomSpec,
                       V1alpha2EndpointSpec, V1alpha2PredictorSpec)
from kubernetes.client import V1Container
from loguru import logger

from .cli import Cli
from .pipeline import Pipeline
from .serve import Serve


class Rollout(Cli):
    NAMESPACE = "kfserving"

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        parser = subparsers.add_parser(command,
                                       help="rollout the deployment image")
        parser.add_argument(
            "--tag",
            "-t",
            type=str,
            metavar="TAG",
            default="latest",
            help="the image tag to be deployed (default: latest)",
        )

    def run(self):
        logger.info("Retrieving kfserving client")
        client = KFServingClient()

        logger.info("Specifying canary")
        canary = V1alpha2EndpointSpec(predictor=V1alpha2PredictorSpec(
            min_replicas=1,
            custom=V1alpha2CustomSpec(container=V1Container(
                name=Serve.SERVICE_NAME,
                image="{}:{}".format(Pipeline.DEPLOY_IMAGE, self.args.tag),
                image_pull_policy="Always",
            ))))

        logger.info("Rolling out canary deployment")
        client.rollout_canary(Serve.SERVICE_NAME,
                              canary=canary,
                              percent=50,
                              namespace=Rollout.NAMESPACE,
                              watch=True)

        logger.info("Promoting canary deployment")
        client.promote(Serve.SERVICE_NAME,
                       namespace=Rollout.NAMESPACE,
                       watch=True)
