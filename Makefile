.PHONY: help install dev test lint format build run clean publish

# Default target
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  install     Install package"
	@echo "  dev         Install with dev dependencies"
	@echo "  test        Run tests"
	@echo "  lint        Run linters (ruff, mypy)"
	@echo "  format      Format code (black, ruff)"
	@echo ""
	@echo "Docker:"
	@echo "  build       Build Docker image"
	@echo "  run         Run CLI in container (usage: make run ARGS='users list agent')"
	@echo "  shell       Open shell in container"
	@echo ""
	@echo "Release:"
	@echo "  dist        Build distribution packages"
	@echo "  publish     Upload to PyPI (use: make publish)"
	@echo "  release     Create GitHub release (use: make release VERSION=0.2.0)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       Remove build artifacts"
	@echo "  clean-all   Remove artifacts and Docker images"

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=insights_sdk --cov-report=term-missing

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

# ─────────────────────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────────────────────

build:
	docker build -t insights .

build-dev:
	docker build -f Dockerfile.dev -t insights:dev .

run:
	docker run --rm \
		-e SCM_CLIENT_ID \
		-e SCM_CLIENT_SECRET \
		-e SCM_TSG_ID \
		-e INSIGHTS_REGION \
		insights $(ARGS)

shell:
	docker run --rm -it --entrypoint /bin/bash \
		-e SCM_CLIENT_ID \
		-e SCM_CLIENT_SECRET \
		-e SCM_TSG_ID \
		insights

docker-test:
	docker build -f Dockerfile.dev -t insights:dev .
	docker run --rm insights:dev

# ─────────────────────────────────────────────────────────────────────────────
# Release
# ─────────────────────────────────────────────────────────────────────────────

dist: clean
	python -m build

publish: dist
	python -m twine upload dist/*

publish-test: dist
	python -m twine upload --repository testpypi dist/*

release:
ifndef VERSION
	$(error VERSION is required. Usage: make release VERSION=0.2.0)
endif
	@echo "Creating release v$(VERSION)..."
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)
	@echo "Release v$(VERSION) created. GitHub Action will publish to PyPI."

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-all: clean
	docker rmi insights insights:dev 2>/dev/null || true
