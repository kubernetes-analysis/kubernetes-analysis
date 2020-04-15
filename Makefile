.PHONY: lint
lint: pylint flake8

.PHONY: flake8
flake8:
	flake8

.PHONY: pylint
pylint:
	bash -c "shopt -s globstar && pylint ./**/*.py"
