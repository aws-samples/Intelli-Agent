.PHONY: format lint test

# Define the root directory and the source directory
ROOT_DIR := $(shell pwd)
SRC_DIR := $(ROOT_DIR)/src

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/
integration_tests: TEST_FILE = tests/integration_tests/

# Run unit tests and generate a coverage report.
coverage coverage_integration_tests:
	poetry run pytest --cov \
		--cov-config=.coveragerc \
		--cov-report xml \
		--cov-report term-missing:skip-covered \
		$(TEST_FILE)

PYTHON_FILES=source/lambda
MYPY_CACHE=.mypy_cache

format format_diff:
	@echo "Formatting code"
	poetry run ruff format $(PYTHON_FILES)
	poetry run ruff --select I --fix $(PYTHON_FILES)

lint lint_diff lint_package lint_tests:
	@echo "Running linter"
	poetry run ruff .
	[ "$(PYTHON_FILES)" = "" ] || poetry run ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || poetry run ruff --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && poetry run mypy $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

# Setup Open Search cluster with Docker
setup_opensearch:
	@echo "Setting up Open Search cluster"
	@echo "Cleaning the existing Open Search container"
	@docker stop $$(docker ps -q --filter ancestor=opensearchproject/opensearch:latest)
	@docker run -d -p 9200:9200 -p 9600:9600 \
		-e "discovery.type=single-node" \
		-e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=LLMBot2024" \
		opensearchproject/opensearch:latest
	@echo "Waiting for Open Search to be ready"
	@for i in {1..30}; do \
		if docker exec $$(docker ps -q -f ancestor=opensearchproject/opensearch:latest) curl -s -k -u admin:LLMBot2024 https://localhost:9200/_cluster/health | grep -q '"status":"green"'; then \
			echo "Open Search is ready!"; \
			break; \
		fi; \
		echo "Waiting for Open Search to start..."; \
		sleep 10; \
	done

test_opensearch: setup_opensearch
	@echo "Running Open Search unit tests"
	@PYTHONPATH=$(SRC_DIR) poetry run pytest $(TEST_FILE)

test tests integration_tests:
	@echo "Running unit tests && integration_tests"
	poetry run pytest $(TEST_FILE)

test_watch:
	poetry run ptw --snapshot-update --now . -- -vv -x tests/unit_tests

# Additional targets for setting up the environment, cleaning build artifacts, etc.
clean:
	@echo "Cleaning up build artifacts"
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf .ruff
	rm -rf .ruff.lock
	rm -rf .ruff.toml
	rm -rf tests/unit_tests/__pycache__
	rm -rf tests/integration_tests/__pycache__
	# stop the Open Search container if it is running
	docker stop $(shell docker ps -q --filter ancestor=opensearchproject/opensearch:latest)

help:
	@echo '----'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo 'coverage                     - run unit tests and generate a coverage report'
	@echo 'clean                        - clean up build artifacts'