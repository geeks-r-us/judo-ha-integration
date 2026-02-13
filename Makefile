.PHONY: help install install-dev setup format lint typecheck test test-cov check clean build install-ha

# Default target
help:
	@echo "Judo iSoft HA Integration - Available targets:"
	@echo ""
	@echo "  setup        Setup development environment"
	@echo "  install      Install runtime dependencies"
	@echo "  install-dev  Install development dependencies"
	@echo "  format       Format code with Black and isort"
	@echo "  lint         Run flake8 linting"
	@echo "  typecheck    Run mypy type checking"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage"
	@echo "  check        Run all quality checks"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo ""
	@echo "Usage examples:"
	@echo "  make setup"
	@echo "  make check"

# Setup development environment
setup: install-dev
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Development environment setup completed!"

# Install runtime dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Format code
format:
	@echo "Formatting code with Black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/
	@echo "Code formatting completed!"

# Run linting
lint:
	@echo "Running flake8 linting..."
	flake8 src/ tests/

# Run type checking
typecheck:
	@echo "Running mypy type checking..."
	mypy src/

# Run tests
test:
	@echo "Running tests..."
	pytest

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=custom_components --cov-report=html --cov-report=term-missing
	@echo "Coverage report available at htmlcov/index.html"

# Run all quality checks
check: format lint typecheck test
	@echo "All quality checks passed!"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/
	@echo "Clean completed!"

# Build package
build: check
	@echo "Building package..."
	python -m build
	@echo "Package built successfully!"
