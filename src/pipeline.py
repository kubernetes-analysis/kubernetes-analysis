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
from .nlp import Nlp


class Pipeline(Cli):
    OUT_DIR = "/out"
    REPO = "kubernetes-analysis"
    IMAGE = "quay.io/saschagrunert/{}:latest".format(REPO)
    FILE = Data.dir_path("pipeline.yaml")

    @staticmethod
    def add_parser(command: str, subparsers: Any):
        subparsers.add_parser(command, help="build the Kubeflow pipeline")

    @staticmethod
    def run():
        logger.info("Building pipeline into {}", Pipeline.FILE)
        Compiler().compile(pipeline_func=Pipeline.__run,
                           package_path=Pipeline.FILE)

    @staticmethod
    @pipeline(name="Kubernetes Analysis")
    def __run(revision: str = "master"):
        # Checkout the source code
        checkout, checkout_outputs = Pipeline.container("checkout",
                                                        dedent("""
                git clone git@github.com:saschagrunert/{repo}
                pushd {repo}
                git checkout {rev}
                popd
            """.format(repo=Pipeline.REPO, rev=revision)),
                                                        outputs={
                                                            "repo":
                                                            Pipeline.REPO,
                                                        })
        repo = checkout_outputs["repo"]

        # Udpate the API data
        update_api, update_api_outputs = Pipeline.container(
            "update-api",
            "./main export --update-api",
            inputs=[repo],
            outputs={
                "api": Data.API_DATA_TARBALL,
            })
        api = update_api_outputs["api"]
        update_api.after(checkout)

        # Udpate the training data from the API
        update_data, update_data_outputs = Pipeline.container(
            "update-data",
            "./main export --update-data",
            inputs=[repo, api],
            outputs={
                "data": Data.TARBALL,
            },
        )
        update_data.after(update_api)
        data = update_data_outputs["data"]

        # Udpate the analysis assets
        update_assets, update_assets_outputs = Pipeline.container(
            "update-assets",
            "echo make assets",
            inputs=[repo, data],
            outputs={"assets": "assets"})
        update_assets.after(update_data)
        assets = update_assets_outputs["assets"]

        # Train the model
        train, train_outputs = Pipeline.container(
            "train",
            "./main train",
            inputs=[repo, data],
            outputs={
                "vectorizer": Nlp.VECTORIZER_FILE,
                "model": Nlp.MODEL_FILE,
            },
        )
        train.after(update_data)
        vectorizer = train_outputs["vectorizer"]
        model = train_outputs["model"]

        # Predict and test the model
        predict, _ = Pipeline.container(
            "predict",
            "/main predict --test",
            inputs=[repo, vectorizer, model],
        )
        predict.after(train)

        # Build Pipeline for verification
        build_pipeline, build_pipeline_outputs = Pipeline.container(
            "build-pipeline",
            "./main pipeline",
            inputs=[repo],
            outputs={
                "pipeline": Pipeline.FILE,
            },
        )
        build_pipeline.after(predict)
        pipe = build_pipeline_outputs["pipeline"]

        # Commit changes
        commit, _ = Pipeline.container(
            "commit-changes",
            dedent("""
              git add .
              git commit -m "Update data" || true
              if [[ {} == master ]]; then
                git push --dry-run
              fi
            """.format(revision)),
            inputs=[repo, api, data, assets, vectorizer, model, pipe],
        )
        commit.after(build_pipeline)

    # yapf: disable
    @staticmethod
    def container(
            name: str,
            arguments: str,
            inputs: Optional[List[Tuple[InputArgumentPath, str]]] = None,
            outputs: Optional[Dict[str, str]] = None,
    ) -> Tuple[ContainerOp, Dict[str, Tuple[InputArgumentPath, str]]]:
        # Set the correct shell parameters
        prepare_args = "set -euo pipefail\n"

        # Copy the output artifacts correctly
        file_outputs = {}
        output_artifact_copy_args = ""
        if outputs:
            for k, v in outputs.items():
                out = Pipeline.out_dir(v)
                file_outputs[k] = out
                output_artifact_copy_args += dedent("""
                    mkdir -p {d}
                    cp -r {fr} {to}
                """.format(
                    d=os.path.dirname(out),
                    fr=v,
                    to=out,
                )).lstrip()

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
        ctr.container.set_image_pull_policy("Always")

        # Set the GitHub token
        token_args = "export GITHUB_TOKEN=$(cat /secret/GITHUB_TOKEN)\n"

        # Copy input artifacts correctly
        input_artifact_copy_args = ""
        for i, path in enumerate(ctr.input_artifact_paths.values()):
            target_location = inputs[i][1]
            input_artifact_copy_args += "cp -r {fr} {to}\n".format(
                fr=path, to=target_location)

            # Change to the repository path if available
            if target_location == Pipeline.REPO:
                input_artifact_copy_args += "cd {}\n".format(Pipeline.REPO)

        # Assemble the command
        ctr.arguments = prepare_args + \
            token_args + \
            input_artifact_copy_args + \
            arguments + \
            "\n" + \
            output_artifact_copy_args

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

        # Assemble the inputs for the next stage
        consumable_inputs = {}
        for k, v in file_outputs.items():
            consumable_inputs[k] = (ctr.outputs[k], outputs[k])

        return ctr, consumable_inputs

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
