COMMIT := $(shell git rev-parse --short HEAD)
PIPELINE ?= "kubernetes-analysis-$(COMMIT)"

.PHONY: pipeline
pipeline:
	./main pipeline

.PHONY: pipeline-run
pipeline-run:
	kfp run submit \
		-e ci \
		-f data/pipeline.yaml \
		-r test-$(COMMIT) \
		revision=$(COMMIT) \
		-w

.PHONY: pipeline-delete
pipeline-delete:
	kfp pipeline delete $(call pipeline-id) || true

.PHONY: assets
assets:
	./main analyze --created -s assets/created-all.svg
	./main analyze --created --issues -s assets/created-issues.svg
	./main analyze --created --pull-requests -s assets/created-pull-requests.svg
	./main analyze --closed -s assets/closed-all.svg
	./main analyze --closed --issues -s assets/closed-issues.svg
	./main analyze --closed --pull-requests -s assets/closed-pull-requests.svg
	./main analyze --created-vs-closed -s assets/created-vs-closed-all.svg
	./main analyze --created-vs-closed --issues -s assets/created-vs-closed-issues.svg
	./main analyze --created-vs-closed --pull-requests -s assets/created-vs-closed-pull-requests.svg
	./main analyze --labels-by-name -s assets/labels-by-name-all-top-25.svg
	./main analyze --labels-by-name --issues -s assets/labels-by-name-issues-top-25.svg
	./main analyze --labels-by-name --pull-requests -s assets/labels-by-name-pull-requests-top-25.svg
	./main analyze --labels-by-group -s assets/labels-by-group-all-top-25.svg
	./main analyze --labels-by-group --issues -s assets/labels-by-group-issues-top-25.svg
	./main analyze --labels-by-group --pull-requests -s assets/labels-by-group-pull-requests-top-25.svg
	./main analyze --users-by-created -s assets/users-by-created-all-top-25.svg
	./main analyze --users-by-created --issues -s assets/users-by-created-issues-top-25.svg
	./main analyze --users-by-created --pull-requests -s assets/users-by-created-pull-requests-top-25.svg
	./main analyze --users-by-closed -s assets/users-by-closed-all-top-25.svg
	./main analyze --users-by-closed --issues -s assets/users-by-closed-issues-top-25.svg
	./main analyze --users-by-closed --pull-requests -s assets/users-by-closed-pull-requests-top-25.svg

.PHONY: lint
lint: pylint flake8

.PHONY: flake8
flake8:
	flake8

.PHONY: pylint
pylint:
	bash -c "shopt -s globstar && pylint ./**/*.py"

.PHONY: update-ci
update-ci:
	$(call replace-config,plugins)
	$(call replace-config,config)
	kubectl delete pods -n default --all

define replace-config
	kubectl -n default create configmap $1 \
			--from-file=$1.yaml=ci/$1.yaml \
			--dry-run=client -o yaml | \
	kubectl -n default replace configmap $1 -f -
endef
