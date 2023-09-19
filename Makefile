.PHONY: \
	tests \
	lint \
	verify \
	install \
	.pre-commit \
	.install-deps

# Project constants
PYTHON_VERSION ?= 2
PYTHON = python$(PYTHON_VERSION)
PYTHON_VENV = venv$(PYTHON_VERSION)

PYTEST_ARGS ?= --cov

PYTEST_CALL = python -B -m pytest $(PYTEST_ARGS)

install-deps:
	virtualenv -p '$(PYTHON)' $(PYTHON_VENV); \
	. $(PYTHON_VENV)/bin/activate; \
	pip install --upgrade -r requirements.txt
	touch $@

pre-commit:
	pre-commit install --install-hooks
	touch $@

install: install-deps pre-commit

tests: install-deps
	. $(PYTHON_VENV)/bin/activate; \
	$(PYTEST_CALL)
