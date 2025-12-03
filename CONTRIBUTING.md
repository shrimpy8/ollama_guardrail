# Contributing to ollama_guardrail

Thank you for your interest in contributing to **ollama_guardrail**! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

---

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and beginners
- Focus on constructive feedback
- Prioritize the community's best interests

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Ollama (running locally)
- OpenAI API key (for OpenAI features)

### Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ollama_guardrail.git
   cd ollama_guardrail
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   # Production dependencies
   pip install -r requirements.txt

   # Development dependencies (includes testing tools)
   pip install -r requirements-dev.txt
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Verify Installation**
   ```bash
   # Run tests
   pytest tests/ -v

   # Start the application
   python app.py
   ```

---

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug Fixes**: Fix issues in existing functionality
- **New Features**: Add new redaction categories or features
- **Documentation**: Improve README, docstrings, or guides
- **Tests**: Add or improve test coverage
- **Performance**: Optimize code performance
- **Security**: Enhance security measures

### Contribution Workflow

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make Your Changes**
   - Write clean, readable code
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run all tests
   pytest tests/ -v

   # Check code coverage
   pytest tests/ --cov=redactor --cov=utils --cov-report=term-missing
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: Add new redaction category for passport numbers"
   ```

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template (see below)

---

## Coding Standards

### Python Style Guide

- Follow **PEP 8** style guidelines
- Use **type hints** for function parameters and return values
- Maximum line length: **100 characters**
- Use **docstrings** for all classes and functions (Google style)

### Example Function

```python
def redact_sensitive_data(
    text: str,
    categories: list[str],
    replacement: str = "[REDACTED]"
) -> dict[str, Any]:
    """
    Redact sensitive information from text based on specified categories.

    Args:
        text: The input text to process
        categories: List of PII categories to redact (e.g., ['email', 'ssn'])
        replacement: String to replace detected PII with

    Returns:
        Dictionary containing:
            - redacted_text: Text with PII redacted
            - detections: List of detected PII items with positions
            - categories_found: Set of categories found in text

    Raises:
        ValueError: If text is empty or categories list is invalid
    """
    # Implementation here
    pass
```

### Code Organization

- **Modular Design**: Keep functions focused on a single responsibility
- **Separation of Concerns**: Business logic in `redactor/`, utilities in `utils/`
- **Configuration**: Use `config.yaml` for configuration, not hardcoded values
- **Constants**: Define constants at the top of modules in UPPER_CASE

---

## Testing Guidelines

### Test Requirements

- All new features **must** include tests
- Bug fixes **should** include regression tests
- Aim for **>80% code coverage** for new code

### Test Structure

```python
# tests/test_new_feature.py
import pytest
from redactor.redactor import SensitiveInformationRedactor

class TestNewFeature:
    """Tests for new redaction feature."""

    @pytest.fixture
    def redactor(self):
        """Create a redactor instance for testing."""
        return SensitiveInformationRedactor()

    def test_redacts_passport_numbers(self, redactor):
        """Test that passport numbers are correctly redacted."""
        text = "My passport is A12345678"
        result = redactor.redact(text, categories=["passport"])

        assert "[REDACTED]" in result["redacted_text"]
        assert "A12345678" not in result["redacted_text"]
        assert len(result["detections"]) == 1
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_redactor.py

# Run with coverage
pytest tests/ --cov=redactor --cov=utils

# Run tests in verbose mode
pytest tests/ -v
```

---

## Commit Message Guidelines

We follow the **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### Examples

```bash
# Feature
feat(redactor): Add passport number detection

# Bug fix
fix(utils): Correct rate limiter token calculation

# Documentation
docs(readme): Add deployment instructions

# Test
test(redactor): Add edge case tests for email detection
```

---

## Pull Request Process

### PR Checklist

Before submitting your PR, ensure:

- [ ] Code follows the style guidelines
- [ ] All tests pass (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, docstrings, SECURITY_NOTICE)
- [ ] No secrets or API keys committed
- [ ] Commit messages follow the guidelines
- [ ] Branch is up to date with `main`

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No secrets committed
```

### Review Process

1. Maintainers will review your PR within 3-5 business days
2. Address any requested changes
3. Once approved, a maintainer will merge your PR

---

## Reporting Bugs

### Before Submitting

- Check existing issues to avoid duplicates
- Test with the latest version
- Gather detailed information

### Bug Report Template

```markdown
**Describe the Bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. ...
2. ...

**Expected Behavior**
What you expected to happen

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.11]
- ollama_guardrail version: [e.g., 1.0.0]

**Additional Context**
- Error messages
- Logs
- Screenshots
```

---

## Feature Requests

We welcome feature requests! Please include:

- **Use Case**: Describe the problem you're trying to solve
- **Proposed Solution**: How you envision the feature working
- **Alternatives**: Other approaches you've considered
- **Additional Context**: Any relevant examples or references

### Example Feature Request

```markdown
**Use Case**
As a compliance officer, I need to redact IBAN numbers from documents.

**Proposed Solution**
Add a new redaction category for International Bank Account Numbers (IBAN).

**Acceptance Criteria**
- Detect IBAN formats from multiple countries
- Include in category dropdown
- Add comprehensive tests

**Additional Context**
IBAN format: https://en.wikipedia.org/wiki/International_Bank_Account_Number
```

---

## Development Tips

### Useful Commands

```bash
# Format code with black
black redactor/ utils/ tests/

# Check code style
flake8 redactor/ utils/ tests/

# Type checking (if using mypy)
mypy redactor/ utils/

# Run specific test
pytest tests/test_redactor.py::TestRedactor::test_redact_email
```

### Project Structure

```
ollama_guardrail/
├── redactor/           # Core redaction logic
│   ├── __init__.py
│   └── redactor.py
├── utils/              # Utility modules
│   ├── config_loader.py
│   ├── rate_limiter.py
│   └── retry_utils.py
├── tests/              # Test suite
│   ├── test_redactor.py
│   ├── test_config_loader.py
│   └── ...
├── app.py              # Main application entry
├── config.yaml         # Configuration file
├── .env.example        # Environment template
└── requirements.txt    # Dependencies
```

---

## Questions?

If you have questions:

1. Check the [README.md](README.md)
2. Review [existing issues](https://github.com/shrimpy8/ollama_guardrail/issues)
3. Open a new issue with the `question` label

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🙏
