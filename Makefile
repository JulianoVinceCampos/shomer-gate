# shomer-gate developer entry points. The CI runs the same targets, so "green
# locally" and "green in CI" mean the same thing.
PYTHON ?= python

.PHONY: help install test lint type eval serve demo gate docker docker-run clean all

help:
	@echo "install    install the package with dev + api extras"
	@echo "test       run the test suite with coverage (ratchet at 85%)"
	@echo "lint       ruff static checks"
	@echo "type       mypy strict type check"
	@echo "eval       score the baseline against ground truth and gate it"
	@echo "serve      run the API + console on :8080"
	@echo "demo       serve the static console only (no backend) on :8000"
	@echo "docker     build the container image"
	@echo "docker-run build and run the container on :8080"
	@echo "all        lint + type + test + eval (what CI runs)"

install:
	$(PYTHON) -m pip install -e ".[dev,api]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

type:
	$(PYTHON) -m mypy

eval:
	$(PYTHON) -m shomer_gate eval

gate: eval

serve:
	$(PYTHON) -m shomer_gate serve

demo:
	$(PYTHON) -m http.server 8000 --directory web

docker:
	docker build -t shomer-gate:0.1.0 .

docker-run: docker
	docker run --rm -p 8080:8080 shomer-gate:0.1.0

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

all: lint type test eval
