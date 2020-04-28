import json
import os
from typing import Any, Dict, List, Optional, Tuple

from kfp.compiler import Compiler
from kfp.dsl import ContainerOp, InputArgumentPath, pipeline
from kubernetes import client as k8s
from loguru import logger

from .cli import Cli
from .data import Data


class Pipeline(Cli):
    OUT_DIR = "/out"
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
        update_api = Pipeline.container(
            "update-api-data",
            ("export GITHUB_TOKEN=$(cat /secret/GITHUB_TOKEN) && "
             "echo ./main -r {} --update-api && "
             "cp data/api.tar.xz /out/api.json").format(revision),
            file_outputs={"api": "/out/api.json"})

        analyze = Pipeline.container(
            "consumer",
            "ls -lah /root/",
            artifacts=[
                (update_api.outputs["api"], "/root/data"),
            ],
        )
        analyze.after(update_api)

    # yapf: disable
    @staticmethod
    def container(
            name: str,
            arguments: str,
            file_outputs: Optional[Dict[str, str]] = None,
            artifacts: Optional[List[Tuple[InputArgumentPath, str]]] = None,
    ) -> ContainerOp:
        ctr = ContainerOp(
            image=Pipeline.IMAGE,
            name=name,
            command=["bash", "-c"],
            output_artifact_paths=Pipeline.default_artifact_path(),
            file_outputs=file_outputs,
            artifact_argument_paths=[
                InputArgumentPath(x[0]) for x in artifacts
            ] if artifacts else None,
        )

        # Copy input artifacts correctly
        input_artifact_copy_args = ""
        for i, path in enumerate(ctr.input_artifact_paths.values()):
            input_artifact_copy_args += "cp {} {} && ".format(
                path, artifacts[i][1])
        ctr.arguments = input_artifact_copy_args + arguments

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
        metadata = "mlpipeline-ui-metadata.json"
        metrics = "mlpipeline-metrics.json"
        return {
            os.path.splitext(metadata)[0]: Pipeline.out_dir(metadata),
            os.path.splitext(metrics)[0]: Pipeline.out_dir(metrics),
        }

    @staticmethod
    def out_dir(path: str) -> str:
        return os.path.join(Pipeline.OUT_DIR, path)
