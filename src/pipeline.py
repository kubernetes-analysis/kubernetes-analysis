import os
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

from kfp.compiler import Compiler
from kfp.dsl import ContainerOp, InputArgumentPath, pipeline
from kubernetes import client as k8s
from loguru import logger

from .cli import Cli
from .data import Data
from .export import Export
from .nlp import Nlp


class Pipeline(Cli):
    OUT_DIR = "/out"
    REPO = "kubernetes-analysis"
    FILE = Data.dir_path("pipeline.yaml")

    IMAGE = "quay.io/saschagrunert/{}:latest".format(REPO)
    DEPLOY_IMAGE = "quay.io/saschagrunert/kubernetes-analysis-kfserving"

    GITHUB_TOKEN_MOUNT_PATH = "/secrets/github"
    QUAY_SECRET_MOUNT_PATH = "/secrets/quay"

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
    def __run(pr: str = "", commit: str = ""):
        # Checkout the source code
        checkout, checkout_outputs = Pipeline.container("checkout",
                                                        dedent("""
                mkdir {repo}
                pushd {repo}
                git init
                git remote add origin git@github.com:{repo}/{repo}

                TARGET="pull/{pr}/head:{pr}"
                REVISION="{pr}"

                if [[ -z "{pr}" ]]; then
                    TARGET=master
                    REVISION=master
                fi

                git fetch --depth=1 origin "$TARGET"
                git checkout "$REVISION"
                popd
            """.format(repo=Pipeline.REPO, pr=pr)),
                                                        outputs={
                                                            "repo":
                                                            Pipeline.REPO,
                                                        })
        repo = checkout_outputs["repo"]

        # Udpate the API data
        update_api, update_api_outputs = Pipeline.container(
            "update-api",
            dedent("""
                export GITHUB_TOKEN=$(cat {path}/GITHUB_TOKEN)
                ./main export --update-api
            """.format(path=Pipeline.GITHUB_TOKEN_MOUNT_PATH)),
            inputs=[repo],
            outputs={
                "api": Data.API_DATA_TARBALL,
                "update-file": Export.API_UPDATE_FILE,
            })
        api = update_api_outputs["api"]
        update_file = update_api_outputs["update-file"]
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
            "make assets",
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
                "selector": Nlp.SELECTOR_FILE,
                "model": Nlp.MODEL_FILE,
            },
        )
        train.container.set_gpu_limit("2")
        train.after(update_data)
        vectorizer = train_outputs["vectorizer"]
        selector = train_outputs["selector"]
        model = train_outputs["model"]

        # Predict and test the model
        predict, _ = Pipeline.container(
            "predict",
            "./main predict --test",
            inputs=[repo, vectorizer, selector, model],
        )
        predict.after(train)

        # Build deployment image
        build_image, _ = Pipeline.container(
            "build-image",
            dedent("""
                buildah bud --isolation=chroot -f Dockerfile-deploy \
                    -t {image}:{commit}

                buildah login -u saschagrunert+kubeflow \
                    -p $(cat {secret}/password) quay.io

                buildah push {image}:{commit}

                if [[ -z "{pr}" ]]; then
                    buildah tag {image}:{commit} {image}:latest
                    buildah push {image}:latest
                fi
            """.format(image=Pipeline.DEPLOY_IMAGE,
                       commit=commit,
                       secret=Pipeline.QUAY_SECRET_MOUNT_PATH,
                       pr=pr)),
            inputs=[repo, vectorizer, selector, model],
        )
        for ctr in ["main", "wait"]:
            build_image.add_pod_annotation(
                "container.apparmor.security.beta.kubernetes.io/" + ctr,
                "unconfined",
            )
        build_image.after(predict)

        # Commit changes
        commit_changes, _ = Pipeline.container(
            "commit-changes",
            dedent("""
              mv assets/data/*.svg assets/
              git add .
              git commit -m "Update data" || true
              if [[ -z "{}" ]]; then
                  git push
              fi
            """.format(pr)),
            inputs=[
                repo, api, update_file, data, assets, vectorizer, selector,
                model
            ],
        )
        commit_changes.after(build_image)

        # Rollout the deployed image
        rollout, _ = Pipeline.container(
            "rollout",
            dedent("""
                if [[ -n "{pr}" ]]; then
                    echo Skipping rollout since this is a PR
                    sleep 10
                    exit 0
                fi

                ./main rollout -t {tag}
            """.format(pr=pr, tag=commit)),
        )
        rollout.after(commit_changes)

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
            artifact_argument_paths=[InputArgumentPath(x[0])
                                     for x in inputs] if inputs else None,
        )
        ctr.container.set_image_pull_policy("Always")

        # Copy input artifacts correctly
        input_artifact_copy_args = ""
        in_repo = False
        for i, path in enumerate(ctr.input_artifact_paths.values()):
            target_location = inputs[i][1]
            input_artifact_copy_args += "cp -r {fr} {to}\n".format(
                fr=path, to=target_location)

            # Change to the repository path if available
            if target_location == Pipeline.REPO:
                in_repo = True
                input_artifact_copy_args += "cd {}\n".format(Pipeline.REPO)
        # Show the git diff to validate
        if in_repo:
            input_artifact_copy_args += dedent("""
                echo "git diff:"
                git diff --name-only
            """)

        # Assemble the command
        ctr.arguments = prepare_args + \
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
                              mount_path=Pipeline.GITHUB_TOKEN_MOUNT_PATH))

        # Quay Login
        quay = "quay"
        ctr.add_volume(
            k8s.V1Volume(name=quay,
                         secret=k8s.V1SecretVolumeSource(secret_name=quay)))
        ctr.container.add_volume_mount(
            k8s.V1VolumeMount(name=quay,
                              read_only=True,
                              mount_path=Pipeline.QUAY_SECRET_MOUNT_PATH))

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
