import json
import os
from textwrap import dedent
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
        archive = Data.dir_path("pipeline.yaml")
        logger.info("Building pipeline into {}", archive)
        Compiler().compile(pipeline_func=Pipeline.__run, package_path=archive)

    @staticmethod
    @pipeline(name="Kubernetes Analysis")
    def __run(revision: str = "master"):
        main = "echo ./main -r {} ".format(revision)

        update_api = Pipeline.container("update-api",
                                        main + "export --update-api",
                                        outputs={
                                            "api": Data.API_DATA_TARBALL,
                                        })

        update_data = Pipeline.container(
            "update-data",
            main + "export --update-data",
            inputs=[
                (update_api.outputs["api"], Data.API_DATA_TARBALL),
            ],
            outputs={
                "data": Data.TARBALL,
            },
        )
        update_data.after(update_api)

    # yapf: disable
    @staticmethod
    def container(
            name: str,
            arguments: str,
            inputs: Optional[List[Tuple[InputArgumentPath, str]]] = None,
            outputs: Optional[Dict[str, str]] = None,
    ) -> ContainerOp:

        # Copy the output artifacts correctly
        file_outputs = {}
        output_artifact_copy_args = ""
        if outputs:
            for k, v in outputs.items():
                out = Pipeline.out_dir(v)
                file_outputs[k] = out
                output_artifact_copy_args += dedent("""
                    mkdir -p {d}
                    cp {fr} {to}
                """.format(
                    d=os.path.dirname(out),
                    fr=v,
                    to=out,
                ))

        # Create the container
        ctr = ContainerOp(
            image=Pipeline.IMAGE,
            name=name,
            command=["bash", "-c"],
            output_artifact_paths=Pipeline.default_artifact_path(),
            file_outputs=file_outputs,
            artifact_argument_paths=[
                InputArgumentPath(x[0]) for x in inputs
            ] if inputs else None,
        )

        # Set the GitHub token
        token_args = "export GITHUB_TOKEN=$(cat /secret/GITHUB_TOKEN)\n"

        # Copy input artifacts correctly
        input_artifact_copy_args = ""
        for i, path in enumerate(ctr.input_artifact_paths.values()):
            input_artifact_copy_args += dedent("""
                cp {fr} {to}
            """.format(fr=path, to=inputs[i][1]))

        # Assemble the command
        ctr.arguments = token_args + input_artifact_copy_args + \
            arguments + "\n" + output_artifact_copy_args

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
