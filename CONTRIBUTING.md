# Contributing to Judo iSoft Home Assistant Integration

Thank you for your interest in contributing to this project! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Home Assistant development environment
- Git

### Setting up the development environment

1. Clone the repository:
```bash
git clone https://github.com/your-username/judo-ha-integration.git
cd judo-ha-integration
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing

### Running code quality checks

```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/

# Run tests
pytest
```

### Running tests with coverage

```bash
pytest --cov=custom_components --cov-report=html
```

## Testing

### Writing Tests

- Place test files in the `tests/` directory
- Follow the naming convention `test_*.py`
- Use descriptive test function names
- Mock external dependencies
- Test both success and failure scenarios

### Test Structure

```python
async def test_feature_success(hass, mock_api):
    """Test feature works correctly."""
    # Arrange
    # Act
    # Assert

async def test_feature_failure(hass, mock_api):
    """Test feature handles errors correctly."""
    # Arrange
    # Act
    # Assert
```

## API Integration

The integration communicates with Judo iSoft systems via HTTP API. When adding new features:

1. Update the `api.py` file with new API methods
2. Add corresponding sensor/binary_sensor entities
3. Update constants in `const.py`
4. Add translations to `strings.json`
5. Write comprehensive tests

### API Method Guidelines

- Use async/await for all network operations
- Handle timeouts and connection errors gracefully
- Log errors appropriately
- Return structured data with sensible defaults

## Entity Development

### Adding New Sensors

1. Add sensor type to `SENSOR_TYPES` in `const.py`:
```python
"new_sensor": {
    "name": "New Sensor",
    "icon": "mdi:icon-name",
    "unit": "unit",
    "device_class": "device_class_if_applicable",
},
```

2. Update sensor logic in `sensor.py`
3. Add API method to fetch data
4. Add translations to `strings.json`
5. Write tests

### Adding New Binary Sensors

Follow similar process for binary sensors using `BINARY_SENSOR_TYPES`.

## Submitting Changes

### Pull Request Process

1. Create a feature branch from `main`:
```bash
git checkout -b feature/description
```

2. Make your changes and commit:
```bash
git add .
git commit -m "feat: add new sensor for X"
```

3. Run all quality checks:
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
pytest
```

4. Push your branch and create a pull request

### Commit Message Format

Use conventional commits format:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

Example: `feat: add salt level monitoring sensor`

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New functionality is tested
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional format
- [ ] No breaking changes without discussion

## Documentation

- Update README.md for significant changes
- Add docstrings to all new functions and classes
- Update configuration examples if needed
- Add comments for complex logic

## Getting Help

If you need help or have questions:

1. Check existing issues on GitHub
2. Create a new issue for bugs or feature requests
3. Start a discussion for questions

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Please be respectful and inclusive in all interactions.

Thank you for contributing!
