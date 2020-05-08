.PHONY: pipeline
pipeline:
	./main pipeline

.PHONY: pipeline-run
pipeline-run: pipeline
	ci/tree-status
	ci/run

.PHONY: assets
assets: \
	assets-created \
	assets-closed \
	assets-created-vs-closed \
	assets-labels-by-name \
	assets-labels-by-group \
	assets-labels-by-created \
	assets-labels-by-closed


.PHONY: assets-created
assets-created:
	./main analyze --created -s assets/created-all.svg
	./main analyze --created --issues -s assets/created-issues.svg
	./main analyze --created --pull-requests -s assets/created-pull-requests.svg

.PHONY: assets-closed
assets-closed:
	./main analyze --closed -s assets/closed-all.svg
	./main analyze --closed --issues -s assets/closed-issues.svg
	./main analyze --closed --pull-requests -s assets/closed-pull-requests.svg

.PHONY: assets-created-vs-closed
assets-created-vs-closed:
	./main analyze --created-vs-closed -s assets/created-vs-closed-all.svg
	./main analyze --created-vs-closed --issues -s assets/created-vs-closed-issues.svg
	./main analyze --created-vs-closed --pull-requests -s assets/created-vs-closed-pull-requests.svg

.PHONY: assets-labels-by-name
assets-labels-by-name:
	./main analyze --labels-by-name -s assets/labels-by-name-all-top-25.svg
	./main analyze --labels-by-name --issues -s assets/labels-by-name-issues-top-25.svg
	./main analyze --labels-by-name --pull-requests -s assets/labels-by-name-pull-requests-top-25.svg

.PHONY: assets-labels-by-group
assets-labels-by-group:
	./main analyze --labels-by-group -s assets/labels-by-group-all-top-25.svg
	./main analyze --labels-by-group --issues -s assets/labels-by-group-issues-top-25.svg
	./main analyze --labels-by-group --pull-requests -s assets/labels-by-group-pull-requests-top-25.svg

.PHONY: assets-labels-by-created
assets-labels-by-created:
	./main analyze --users-by-created -s assets/users-by-created-all-top-25.svg
	./main analyze --users-by-created --issues -s assets/users-by-created-issues-top-25.svg
	./main analyze --users-by-created --pull-requests -s assets/users-by-created-pull-requests-top-25.svg

.PHONY: assets-labels-by-closed
assets-labels-by-closed:
	./main analyze --users-by-closed -s assets/users-by-closed-all-top-25.svg
	./main analyze --users-by-closed --issues -s assets/users-by-closed-issues-top-25.svg
	./main analyze --users-by-closed --pull-requests -s assets/users-by-closed-pull-requests-top-25.svg

.PHONY: lint
lint:
	ci/lint

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

.PHONY: update-plugin
update-plugin:
	IMAGE=quay.io/saschagrunert/kubernetes-analysis-plugin:latest && \
	buildah bud -f Dockerfile-plugin -t $$IMAGE && \
	buildah push $$IMAGE
	kubectl apply -f deploy/plugin.yaml
	kubectl -n default delete pod \
		$(shell kubectl -n default get pods \
			-l app=kubernetes-analysis \
			--no-headers \
			-o custom-columns=":metadata.name")

.PHONY: go-build
go-build:
	go build \
		-tags "netgo" \
		-ldflags '-s -w -linkmode external -extldflags "-static -lm"'

.PHONY: go-test
go-test:
	go test -v -count=1 -cover -coverprofile coverage.out ./... $(ARGS)
	go tool cover -html coverage.out -o coverage.html
