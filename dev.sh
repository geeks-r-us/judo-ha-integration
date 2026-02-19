#!/bin/bash

# Judo iSoft HA Integration Development Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_warning "No virtual environment detected. Consider activating one."
    fi
}

# Install dependencies
install_deps() {
    print_status "Installing dependencies..."
    pip install -r requirements-dev.txt
    print_success "Dependencies installed"
}

# Install pre-commit hooks
install_hooks() {
    print_status "Installing pre-commit hooks..."
    pre-commit install
    print_success "Pre-commit hooks installed"
}

# Format code
format_code() {
    print_status "Formatting code with Black..."
    black src/ tests/

    print_status "Sorting imports with isort..."
    isort src/ tests/

    print_success "Code formatting completed"
}

# Run linting
lint_code() {
    print_status "Running flake8 linting..."
    flake8 src/ tests/
    print_success "Linting passed"
}

# Run type checking
type_check() {
    print_status "Running mypy type checking..."
    mypy src/
    print_success "Type checking passed"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    pytest
    print_success "Tests passed"
}

# Run tests with coverage
run_tests_coverage() {
    print_status "Running tests with coverage..."
    pytest --cov=custom_components --cov-report=html --cov-report=term-missing
    print_success "Tests with coverage completed"
    print_status "Coverage report available at htmlcov/index.html"
}

# Run all quality checks
check_all() {
    print_status "Running all quality checks..."
    format_code
    lint_code
    type_check
    run_tests
    print_success "All checks passed!"
}

# Setup development environment
setup_dev() {
    print_status "Setting up development environment..."
    check_venv
    install_deps
    install_hooks
    print_success "Development environment setup completed"
}

# Clean build artifacts
clean() {
    print_status "Cleaning build artifacts..."
    rm -rf build/ dist/ *.egg-info/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf .pytest_cache/ .coverage htmlcov/
    print_success "Clean completed"
}

# Build package
build_package() {
    print_status "Building package..."
    python -m build
    print_success "Package built successfully"
}

# Copy integration to Home Assistant config
install_ha() {
    if [[ -z "$1" ]]; then
        print_error "Usage: $0 install-ha /path/to/homeassistant/config"
        exit 1
    fi

    HA_CONFIG_PATH="$1"
    CUSTOM_COMPONENTS_PATH="$HA_CONFIG_PATH/custom_components"
    TARGET_PATH="$CUSTOM_COMPONENTS_PATH/judo_isoft"

    print_status "Installing integration to Home Assistant config..."

    # Create custom_components directory if it doesn't exist
    mkdir -p "$CUSTOM_COMPONENTS_PATH"

    # Remove existing installation
    if [[ -d "$TARGET_PATH" ]]; then
        rm -rf "$TARGET_PATH"
    fi

    # Copy integration files
    cp -r custom_components/judo_isoft "$TARGET_PATH"

    print_success "Integration installed to $TARGET_PATH"
    print_warning "Please restart Home Assistant to load the integration"
}

# Show help
show_help() {
    echo "Judo iSoft HA Integration Development Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup        Setup development environment"
    echo "  install      Install dependencies"
    echo "  hooks        Install pre-commit hooks"
    echo "  format       Format code with Black and isort"
    echo "  lint         Run flake8 linting"
    echo "  typecheck    Run mypy type checking"
    echo "  test         Run tests"
    echo "  test-cov     Run tests with coverage"
    echo "  check        Run all quality checks"
    echo "  clean        Clean build artifacts"
    echo "  build        Build package"
    echo "  install-ha   Install to Home Assistant config (requires path)"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 check"
    echo "  $0 install-ha /home/user/.homeassistant"
}

# Main script logic
case "${1:-help}" in
    setup)
        setup_dev
        ;;
    install)
        install_deps
        ;;
    hooks)
        install_hooks
        ;;
    format)
        format_code
        ;;
    lint)
        lint_code
        ;;
    typecheck)
        type_check
        ;;
    test)
        run_tests
        ;;
    test-cov)
        run_tests_coverage
        ;;
    check)
        check_all
        ;;
    clean)
        clean
        ;;
    build)
        build_package
        ;;
    install-ha)
        install_ha "$2"
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
