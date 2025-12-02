"""
Pytest Configuration and Shared Fixtures

This module provides shared fixtures and configuration for all tests.

Author: Harsh
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_config_file():
    """Create a temporary config.yaml file for testing."""
    config_content = """
models:
  ollama:
    name: "llama3.2:latest"
    timeout: 120
  openai:
    name: "gpt-3.5-turbo"
    timeout: 60
    temperature: 0.7
    max_tokens: 2000

retry:
  max_attempts: 3
  min_wait: 2
  max_wait: 10
  multiplier: 2

rate_limiting:
  enabled: true
  max_requests_per_minute: 60
  max_tokens_per_minute: 90000

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "app.log"
  console: true
  file_logging: true
  max_bytes: 10485760
  backup_count: 5

ui:
  title: "Sensitive Information Redaction Tool"
  description: "Identify and redact sensitive information from text"
  theme: "default"
  share: false
  server:
    port: 7860
    host: "127.0.0.1"
  components:
    input_text:
      lines: 10
      placeholder: "Enter text to analyze..."
    output_text:
      lines: 10
    category_selection:
      default_all: false

categories:
  enabled:
    - name: "Email Addresses"
      placeholder: "[EMAIL-{index}]"
      description: "Redact email addresses"
    - name: "Phone Numbers"
      placeholder: "[PHONE-{index}]"
      description: "Redact phone numbers"

openai_processing:
  instruction_prefix: "Process the following text:\\n"
  enable_automatic_submit: false

security:
  validate_api_key_on_startup: true
  sanitize_error_messages: true
  log_sensitive_data: false

features:
  batch_processing: false
  custom_rules: false
  export_results: true
  api_mode: false
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    env_content = "OPENAI_API_KEY=test-key-123\n"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def mock_ollama_model():
    """Create a mock Ollama model for testing."""
    mock = MagicMock()
    mock.invoke.return_value = '{"redacted_text": "Test [EMAIL-1]", "detected_sensitive_data": [{"type": "email", "value": "test@example.com", "placeholder": "[EMAIL-1]"}]}'
    return mock


@pytest.fixture
def mock_openai_model():
    """Create a mock OpenAI model for testing."""
    mock = MagicMock()
    response = Mock()
    response.content = "This is a test response from OpenAI"
    mock.invoke.return_value = response
    return mock


@pytest.fixture
def sample_text():
    """Provide sample text for testing redaction."""
    return "My email is john.doe@example.com and my phone is 555-123-4567"


@pytest.fixture
def sample_categories():
    """Provide sample categories for testing."""
    return ["Email Addresses", "Phone Numbers"]


@pytest.fixture
def sample_category_map():
    """Provide sample category map for testing."""
    return {
        "Email Addresses": "[EMAIL-1]",
        "Phone Numbers": "[PHONE-1]"
    }


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset ConfigLoader singleton between tests."""
    from utils.config_loader import ConfigLoader
    ConfigLoader._instance = None
    yield
    ConfigLoader._instance = None


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before and after tests."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()
