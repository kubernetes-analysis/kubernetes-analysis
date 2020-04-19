.PHONY: assets
assets:
	./analyze --created -s assets/created-all.svg
	./analyze --created --issues -s assets/created-issues.svg
	./analyze --created --pull-requests -s assets/created-pull-requests.svg
	./analyze --closed -s assets/closed-all.svg
	./analyze --closed --issues -s assets/closed-issues.svg
	./analyze --closed --pull-requests -s assets/closed-pull-requests.svg
	./analyze --created-vs-closed -s assets/created-vs-closed-all.svg
	./analyze --created-vs-closed --issues -s assets/created-vs-closed-issues.svg
	./analyze --created-vs-closed --pull-requests -s assets/created-vs-closed-pull-requests.svg
	./analyze --labels-by-name -s assets/labels-by-name-all-top-25.svg
	./analyze --labels-by-name --issues -s assets/labels-by-name-issues-top-25.svg
	./analyze --labels-by-name --pull-requests -s assets/labels-by-name-pull-requests-top-25.svg
	./analyze --labels-by-group -s assets/labels-by-group-all-top-25.svg
	./analyze --labels-by-group --issues -s assets/labels-by-group-issues-top-25.svg
	./analyze --labels-by-group --pull-requests -s assets/labels-by-group-pull-requests-top-25.svg
	./analyze --users-by-created -s assets/users-by-created-all-top-25.svg
	./analyze --users-by-created --issues -s assets/users-by-created-issues-top-25.svg
	./analyze --users-by-created --pull-requests -s assets/users-by-created-pull-requests-top-25.svg
	./analyze --users-by-closed -s assets/users-by-closed-all-top-25.svg
	./analyze --users-by-closed --issues -s assets/users-by-closed-issues-top-25.svg
	./analyze --users-by-closed --pull-requests -s assets/users-by-closed-pull-requests-top-25.svg

.PHONY: lint
lint: pylint flake8

.PHONY: flake8
flake8:
	flake8

.PHONY: pylint
pylint:
	bash -c "shopt -s globstar && pylint ./**/*.py"
