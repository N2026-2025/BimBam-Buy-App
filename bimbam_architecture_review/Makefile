# BimBam Architecture Review - Makefile
# Common development tasks

.PHONY: help install test lint format type-check clean build docker-build docker-run docs

# Default target
help:
	@echo "BimBam Architecture Review - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install       Install package in development mode"
	@echo "  install-dev   Install with development dependencies"
	@echo "  test          Run tests with coverage"
	@echo "  test-watch    Run tests in watch mode"
	@echo "  lint          Run linting (ruff)"
	@echo "  format        Format code (black + isort)"
	@echo "  type-check    Run type checking (mypy)"
	@echo "  pre-commit    Run pre-commit hooks"
	@echo ""
	@echo "Building:"
	@echo "  build         Build package distribution"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"
	@echo "  docker-compose-up  Start all services"
	@echo "  docker-compose-down Stop all services"
	@echo ""
	@echo "Review:"
	@echo "  review        Run architecture review"
	@echo "  review-api    Start API server"
	@echo "  extract       Extract principles from PDFs"
	@echo ""
	@echo "Documentation:"
	@echo "  docs          Build documentation"
	@echo "  docs-serve    Serve documentation locally"

# =============================================================================
# Development
# =============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=bimbam_architecture_review --cov-report=term-missing

test-watch:
	pytest-watch tests/ -- -v

test-unit:
	pytest tests/ -v -m "not integration" --cov=bimbam_architecture_review

test-integration:
	pytest tests/ -v -m integration

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	isort src/ tests/

type-check:
	mypy src/bimbam_architecture_review

pre-commit:
	pre-commit run --all-files

# =============================================================================
# Building
# =============================================================================

build: clean
	python -m build

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker build -t bimbam-architecture-review:latest .

docker-build-dev:
	docker build -t bimbam-architecture-review:dev --target builder .

docker-run:
	docker run --rm -it \
		-v $(PWD)/documents:/app/documents:ro \
		-v $(PWD)/reports:/app/reports \
		-v $(PWD)/config:/app/config:ro \
		-p 8000:8000 \
		bimbam-architecture-review:latest \
		review --documents /app/documents --system-path /app/bimbam-buy-ai-agent --output /app/reports

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

docker-compose-logs:
	docker-compose logs -f

docker-compose-restart:
	docker-compose restart

# =============================================================================
# Architecture Review Commands
# =============================================================================

review:
	bimbam-architecture-review review \
		--documents ./documents \
		--system-path ./bimbam-buy-ai-agent \
		--output ./reports \
		--format console --format json --format markdown --format html

review-full:
	bimbam-architecture-review review \
		--documents ./documents \
		--system-path ./bimbam-buy-ai-agent \
		--output ./reports \
		--format console --format json --format markdown --format html --format pdf \
		--severity critical --severity high --severity medium --severity low \
		--parallel 4

review-api:
	bimbam-architecture-review serve --host 0.0.0.0 --port 8000 --reload

extract:
	bimbam-architecture-review extract \
		--documents ./documents \
		--output ./extracted/principles.json

roadmap:
	bimbam-architecture-review roadmap \
		--analysis ./reports/latest.json \
		--output ./reports/roadmap.md \
		--timeline 12

executive:
	bimbam-architecture-review executive \
		--analysis ./reports/latest.json \
		--output ./reports/executive_summary.md

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Documentation is in README.md and wiki"

docs-serve:
	@echo "Start a local server to view docs:"
	@echo "  python -m http.server 8080 -d ./docs"

# =============================================================================
# CI/CD Helpers
# =============================================================================

ci-test:
	pytest tests/ -v --cov=bimbam_architecture_review --cov-report=xml --junitxml=junit.xml

ci-lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

ci-type-check:
	mypy src/bimbam_architecture_review

ci-security:
	bandit -r src/
	pip-audit -r requirements.txt

ci-all: ci-lint ci-type-check ci-test ci-security

# =============================================================================
# Release
# =============================================================================

version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major

release: clean build
	twine check dist/*
	@echo "Ready to publish: twine upload dist/*"

# =============================================================================
# Utility
# =============================================================================

check-deps:
	pip list --outdated

update-deps:
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt
	pip freeze > requirements-lock.txt

shell:
	docker run --rm -it \
		-v $(PWD):/app \
		-w /app \
		bimbam-architecture-review:latest \
		/bin/bash

logs:
	docker-compose logs -f architecture-review

status:
	@echo "=== Docker Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Disk Usage ==="
	@df -h .
	@echo ""
	@echo "=== Python Packages ==="
	@pip list | grep -E "(bimbam|pydantic|fastapi|typer|rich)"