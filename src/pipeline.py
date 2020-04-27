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
        update_api = Pipeline.container("update-api-data", revision)

        analyze = Pipeline.container("analyze-data", revision)
        analyze.after(update_api)

    @staticmethod
    def container(
            name: str,
            revision: str,
    ) -> ContainerOp:
        ctr = ContainerOp(
            image=Pipeline.IMAGE,
            name=name,
            command=["bash", "-c"],
            arguments=("export GITHUB_TOKEN=$(cat /secret/GITHUB_TOKEN) && "
                       "echo Running step {name} for revision {revision} && "
                       "echo {meta} > {meta_path}").format(
                           name=name,
                           revision=revision,
                           meta=Pipeline.markdown_metadata(name),
                           meta_path=Pipeline.METADATA_FILE_PATH),
            output_artifact_paths=Pipeline.default_artifact_path())

        # Output Artifacts
        vol = "output-artifacts"
        ctr.add_volume(
            k8s.V1Volume(name=vol, empty_dir=k8s.V1EmptyDirVolumeSource()))
        ctr.container.add_volume_mount(
            k8s.V1VolumeMount(name=vol, mount_path=Pipeline.OUT_DIR))

        # GitHub Token
        gh_token = "github-token"
        ctr.add_volume(
            k8s.V1Volume(
                name=gh_token,
                secret=k8s.V1SecretVolumeSource(secret_name=gh_token)))
        ctr.container.add_volume_mount(
            k8s.V1VolumeMount(name=gh_token,
                              read_only=True,
                              mount_path="/secret"))

        # SSH Key
        ssh_key = "ssh-key"
        ctr.add_volume(
            k8s.V1Volume(name=ssh_key,
                         secret=k8s.V1SecretVolumeSource(default_mode=0o600,
                                                         secret_name=ssh_key)))
        ctr.container.add_volume_mount(
            k8s.V1VolumeMount(name=ssh_key,
                              read_only=True,
                              mount_path="/root/.ssh"))

        return ctr

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
