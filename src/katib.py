import json
from functools import wraps
from textwrap import dedent
from typing import List

from .data import Data


def trial_template(name, image, replicas, command, mount_path, pr=None):
    target = "pull/{pr}/head:{pr}".format(pr=pr) if pr else "master"
    revision = pr if pr else "master"
    args = ["cd data/kubernetes-analysis ;",
            "git fetch origin {} ;".format(target),
            "git checkout {} ;".format(revision),
            "./main tune {{- with .HyperParameters}} {{- range .}} {{.Name}}={{.Value}} {{- end}} {{- end}}"]

    return {
        "apiVersion": "kubeflow.org/v1",
        "kind": "TFJob",
        "metadata": {
            "name": "{{.Trial}}",
            "namespace": "{{.NameSpace}}"
        },
        "spec": {
            "tfReplicaSpecs": {
                "Worker": {
                    "replicas": replicas,
                    "restartPolicy": "OnFailure",
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": name,
                                "image": image,
                                "imagePullPolicy": "Always",
                                "command": ["bash", "-c"],
                                "args": args,
                                "volumeMounts": [{
                                    "mountPath": "/data",
                                    "name": "nfs-storage"
                                }]
                            }],
                            "volumes": [{
                                "name": "nfs-storage",
                                "persistentVolumeClaim": {
                                    "claimName": "pipeline-pv"
                                }
                            }]
                        }
                    }
                }
            }
        }
    }


class KatibOp():
    is_created = False

    def __init__(self, image: str, name, output: str, repo: str, pr: str):
        self.repo = repo
        self.pr = pr
        self.output = output
        self.name = name
        self.image = image
        self.controller_img = "mbu93/katib-launcher:latest"
        self.with_objective("maximize", 0.8, "Accuracy")
        self.with_algorithm("random")

        self.with_parameters(["layers", "units"], ["int", "int"], [
                             {"min": "1", "max": "3"}, {"min": "8", "max": "16"}])
        self.with_trial_template(
            name="tensorflow",
            image=image,
            replicas=1,
            command="tune")
        self.with_metrics_collector_spec("StdOut")
        self.template_path = Data.dir_path("katib_component.yaml")
        self.create()
        self.is_created = True

    def rebuild(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            self = args[0]
            func(*args, **kwargs)
            if self.is_created:
                self.create()
        return wrap

    @rebuild
    def with_objective(self, goal_type: str, goal: float, metric: str):
        self.objectiveConfig = {
            "type": goal_type,
            "goal": goal,
            "objectiveMetricName": metric,
        }
        return self

    @rebuild
    def with_algorithm(self, algorithm_type: str):
        self.algorithmConfig = {"algorithmName": algorithm_type}
        return self

    @rebuild
    def with_parameters(self, names: List[str], types: List[str], spaces: List[dict]):
        self.parameters = [{"name": "--" + x, "parameterType": y, "feasibleSpace": z}
                           for x, y, z in zip(names, types, spaces)]
        return self

    @rebuild
    def with_trial_template(self, image: str, name: str, replicas: int, command: str):
        rawTemplate = trial_template(name, image, replicas, command, self.output, self.pr)
        self.trialTemplate = {
            "goTemplate": {
                "rawTemplate": json.dumps(rawTemplate)
            }
        }
        return self

    @rebuild
    def with_metrics_collector_spec(self, kind: str):
        self.metricsCollectorSpec = {
            "collector": {
                "kind": kind
            }
        }
        return self

    def create(self):
        self.op = dedent("""
        rm -rf {outdir}/{repo}
        git clone https://github.com/saschagrunert/{repo} {outdir}/{repo}
        python /ml/launch_experiment.py \
--name {} \
--namespace {} \
--maxTrialCount {} \
--parallelTrialCount {} \
--objectiveConfig '{}' \
--algorithmConfig '{}' \
--trialTemplate '{}' \
--parameters '{}' \
--metricsCollector '{}' \
--experimentTimeoutMinutes '{}' \
--deleteAfterDone {} \
--outputFile results/params
        """.format(
            self.name,
            "kubeflow",
            1,
            1,
            json.dumps(self.objectiveConfig),
            json.dumps(self.algorithmConfig),
            json.dumps(self.trialTemplate),
            json.dumps(self.parameters),
            json.dumps(self.metricsCollectorSpec),
            15,
            True,
            outdir=self.output,
            repo=self.repo,
        ))
