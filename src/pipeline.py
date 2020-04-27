import json
import os
from typing import Any, Dict

from kfp.compiler import Compiler
from kfp.dsl import ContainerOp, ExitHandler, pipeline
from kubernetes import client as k8s
from loguru import logger

from .cli import Cli
from .data import Data


class Pipeline(Cli):
    OUT_DIR = "/out"
    METADATA_FILE = "mlpipeline-ui-metadata.json"
    METRICS_FILE = "mlpipeline-metrics.json"
    METADATA_FILE_PATH = os.path.join(OUT_DIR, METADATA_FILE)
    METRICS_FILE_PATH = os.path.join(OUT_DIR, METRICS_FILE)
    IMAGE = "quay.io/saschagrunert/kubernetes-analysis:latest"

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        subparsers.add_parser(command, help="build the Kubeflow pipeline")

    @staticmethod
    def run():
        archive = Data.dir_path("pipeline.tar.gz")
        logger.info("Building pipeline into {}", archive)
        Compiler().compile(pipeline_func=Pipeline.__run, package_path=archive)

    @staticmethod
    @pipeline(name="Kubernetes Analysis")
    def __run(revision: str = "master"):
        deploy = Pipeline.container("deploy", revision, is_exit_handler=True)
        with ExitHandler(deploy):
            deps = Pipeline.container("setup dependencies", revision)

            analyze = Pipeline.container("analyze data", revision)
            analyze.after(deps)

            train1 = Pipeline.container("training 1", revision)
            train1.after(analyze)

    @staticmethod
    def container(name: str,
                  revision: str,
                  is_exit_handler=False) -> ContainerOp:
        operation = ContainerOp(
            image=Pipeline.IMAGE,
            name=name,
            command=["bash", "-c"],
            arguments=[
                "echo Running step $0 for revision $1 && echo $2 > $3",
                name,
                revision,
                Pipeline.markdown_metadata(name),
                Pipeline.METADATA_FILE_PATH,
            ],
            is_exit_handler=is_exit_handler,
            output_artifact_paths=Pipeline.default_artifact_path())

        volume = "volume"
        operation.add_volume(
            k8s.V1Volume(name=volume, empty_dir=k8s.V1EmptyDirVolumeSource()))
        operation.container.add_volume_mount(
            k8s.V1VolumeMount(name=volume, mount_path=Pipeline.OUT_DIR))
        return operation

    @staticmethod
    def markdown_metadata(result: str) -> str:
        return json.dumps({
            "outputs": [{
                "type": "markdown",
                "source": "The result: %s" % result,
                "storage": "inline",
            }]
        })

    @staticmethod
    def default_artifact_path() -> Dict[str, str]:
        return {
            os.path.splitext(Pipeline.METADATA_FILE)[0]:
            Pipeline.METADATA_FILE_PATH,
            os.path.splitext(Pipeline.METRICS_FILE)[0]:
            Pipeline.METRICS_FILE_PATH,
        }
