# Geospatial Data Downloader - Development Commands
# =================================================

.PHONY: help install install-dev clean test test-unit test-integration test-e2e
.PHONY: lint format type-check security quality pre-commit-install
.PHONY: run-api run-streamlit build docs

# Default target
help:	## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation commands
install:	## Install production dependencies
	pip install -r requirements.txt

install-dev:	## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

# Code quality commands
format:	## Format code with black and isort
	black .
	isort .

lint:	## Run linting with flake8
	flake8 .

type-check:	## Run type checking with mypy
	mypy src/

security:	## Run security checks
	bandit -r src/ -f json -o bandit-report.json
	safety check

quality: format lint type-check security	## Run all code quality checks

# Pre-commit setup
pre-commit-install:	## Install pre-commit hooks
	pre-commit install

# Testing commands
test:	## Run all tests
	pytest

test-unit:	## Run unit tests only
	pytest tests/unit/ -v

test-integration:	## Run integration tests only
	pytest tests/integration/ -v

test-e2e:	## Run end-to-end tests only
	pytest tests/e2e/ -v

test-coverage:	## Run tests with coverage report
	pytest --cov=src/geospatial_downloader --cov-report=html --cov-report=term-missing

# Application commands
run-api:	## Start the FastAPI server
	python start_api.py

run-streamlit:	## Start the Streamlit application
	python -m streamlit run streamlit_app.py

# Build commands
clean:	## Clean build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

build:	## Build package
	python -m build

# Documentation
docs:	## Generate documentation
	cd docs && make html

# Development workflow
dev-setup: install-dev pre-commit-install	## Complete development setup
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify everything works."

check: quality test	## Run all quality checks and tests