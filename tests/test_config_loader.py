"""
Unit Tests for ConfigLoader

Tests for the configuration management system.

Author: Harsh
"""

import pytest
import os
import yaml
from utils.config_loader import ConfigLoader, load_config


@pytest.mark.unit
class TestConfigLoader:
    """Test suite for ConfigLoader class."""

    def test_singleton_pattern(self, temp_config_file):
        """Test that ConfigLoader implements singleton pattern."""
        config1 = ConfigLoader(temp_config_file)
        config2 = ConfigLoader(temp_config_file)

        assert config1 is config2, "ConfigLoader should be a singleton"

    def test_load_config_convenience_function(self, temp_config_file):
        """Test the load_config convenience function."""
        config = load_config(temp_config_file)

        assert isinstance(config, ConfigLoader)
        assert config.get_ollama_model_name() == "llama3.2:latest"

    def test_file_not_found_error(self):
        """Test that FileNotFoundError is raised for missing config file."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader("nonexistent_config.yaml")

    def test_invalid_yaml_error(self, tmp_path):
        """Test that YAMLError is raised for invalid YAML."""
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            ConfigLoader(str(invalid_config))


@pytest.mark.unit
class TestModelConfiguration:
    """Test suite for model configuration methods."""

    def test_get_ollama_model_name(self, temp_config_file):
        """Test getting Ollama model name."""
        config = ConfigLoader(temp_config_file)
        assert config.get_ollama_model_name() == "llama3.2:latest"

    def test_get_ollama_timeout(self, temp_config_file):
        """Test getting Ollama timeout."""
        config = ConfigLoader(temp_config_file)
        assert config.get_ollama_timeout() == 120

    def test_get_openai_model_name(self, temp_config_file):
        """Test getting OpenAI model name."""
        config = ConfigLoader(temp_config_file)
        assert config.get_openai_model_name() == "gpt-3.5-turbo"

    def test_get_openai_timeout(self, temp_config_file):
        """Test getting OpenAI timeout."""
        config = ConfigLoader(temp_config_file)
        assert config.get_openai_timeout() == 60

    def test_get_openai_temperature(self, temp_config_file):
        """Test getting OpenAI temperature."""
        config = ConfigLoader(temp_config_file)
        assert config.get_openai_temperature() == 0.7

    def test_get_openai_max_tokens(self, temp_config_file):
        """Test getting OpenAI max tokens."""
        config = ConfigLoader(temp_config_file)
        assert config.get_openai_max_tokens() == 2000


@pytest.mark.unit
class TestRetryConfiguration:
    """Test suite for retry configuration methods."""

    def test_get_retry_config(self, temp_config_file):
        """Test getting complete retry configuration."""
        config = ConfigLoader(temp_config_file)
        retry_config = config.get_retry_config()

        assert retry_config['max_attempts'] == 3
        assert retry_config['min_wait'] == 2
        assert retry_config['max_wait'] == 10
        assert retry_config['multiplier'] == 2

    def test_get_max_retry_attempts(self, temp_config_file):
        """Test getting max retry attempts."""
        config = ConfigLoader(temp_config_file)
        assert config.get_max_retry_attempts() == 3


@pytest.mark.unit
class TestRateLimitingConfiguration:
    """Test suite for rate limiting configuration methods."""

    def test_is_rate_limiting_enabled(self, temp_config_file):
        """Test rate limiting enabled check."""
        config = ConfigLoader(temp_config_file)
        assert config.is_rate_limiting_enabled() is True

    def test_get_max_requests_per_minute(self, temp_config_file):
        """Test getting max requests per minute."""
        config = ConfigLoader(temp_config_file)
        assert config.get_max_requests_per_minute() == 60

    def test_get_max_tokens_per_minute(self, temp_config_file):
        """Test getting max tokens per minute."""
        config = ConfigLoader(temp_config_file)
        assert config.get_max_tokens_per_minute() == 90000


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test suite for logging configuration methods."""

    def test_get_logging_config(self, temp_config_file):
        """Test getting complete logging configuration."""
        config = ConfigLoader(temp_config_file)
        logging_config = config.get_logging_config()

        assert logging_config['level'] == 'INFO'
        assert logging_config['file'] == 'app.log'
        assert logging_config['console'] is True
        assert logging_config['file_logging'] is True
        assert logging_config['max_bytes'] == 10485760
        assert logging_config['backup_count'] == 5


@pytest.mark.unit
class TestUIConfiguration:
    """Test suite for UI configuration methods."""

    def test_get_ui_title(self, temp_config_file):
        """Test getting UI title."""
        config = ConfigLoader(temp_config_file)
        assert config.get_ui_title() == "Sensitive Information Redaction Tool"

    def test_get_ui_description(self, temp_config_file):
        """Test getting UI description."""
        config = ConfigLoader(temp_config_file)
        assert "Identify and redact sensitive information" in config.get_ui_description()

    def test_get_ui_theme(self, temp_config_file):
        """Test getting UI theme."""
        config = ConfigLoader(temp_config_file)
        assert config.get_ui_theme() == "default"

    def test_get_ui_share(self, temp_config_file):
        """Test getting UI share setting."""
        config = ConfigLoader(temp_config_file)
        assert config.get_ui_share() is False

    def test_get_server_config(self, temp_config_file):
        """Test getting server configuration."""
        config = ConfigLoader(temp_config_file)
        server_config = config.get_server_config()

        assert server_config['port'] == 7860
        assert server_config['host'] == "127.0.0.1"

    def test_get_input_text_config(self, temp_config_file):
        """Test getting input text component configuration."""
        config = ConfigLoader(temp_config_file)
        input_config = config.get_input_text_config()

        assert input_config['lines'] == 10
        assert "Enter text to analyze" in input_config['placeholder']

    def test_get_output_text_config(self, temp_config_file):
        """Test getting output text component configuration."""
        config = ConfigLoader(temp_config_file)
        output_config = config.get_output_text_config()

        assert output_config['lines'] == 10

    def test_get_category_selection_default_all(self, temp_config_file):
        """Test getting category selection default setting."""
        config = ConfigLoader(temp_config_file)
        assert config.get_category_selection_default_all() is False


@pytest.mark.unit
class TestCategoryConfiguration:
    """Test suite for category configuration methods."""

    def test_get_redaction_categories(self, temp_config_file):
        """Test getting redaction categories."""
        config = ConfigLoader(temp_config_file)
        categories = config.get_redaction_categories()

        assert len(categories) == 2
        assert categories[0]['name'] == "Email Addresses"
        assert categories[1]['name'] == "Phone Numbers"

    def test_get_category_map(self, temp_config_file):
        """Test getting category map."""
        config = ConfigLoader(temp_config_file)
        category_map = config.get_category_map()

        assert "Email Addresses" in category_map
        assert "Phone Numbers" in category_map
        assert category_map["Email Addresses"] == "[EMAIL-1]"
        assert category_map["Phone Numbers"] == "[PHONE-1]"

    def test_get_category_options(self, temp_config_file):
        """Test getting category options."""
        config = ConfigLoader(temp_config_file)
        options = config.get_category_options()

        assert len(options) == 2
        assert "Email Addresses" in options
        assert "Phone Numbers" in options


@pytest.mark.unit
class TestOpenAIProcessingConfiguration:
    """Test suite for OpenAI processing configuration methods."""

    def test_get_openai_instruction_prefix(self, temp_config_file):
        """Test getting OpenAI instruction prefix."""
        config = ConfigLoader(temp_config_file)
        prefix = config.get_openai_instruction_prefix()

        assert "Process the following text" in prefix

    def test_is_auto_submit_enabled(self, temp_config_file):
        """Test auto-submit setting."""
        config = ConfigLoader(temp_config_file)
        assert config.is_auto_submit_enabled() is False


@pytest.mark.unit
class TestSecurityConfiguration:
    """Test suite for security configuration methods."""

    def test_should_validate_api_key_on_startup(self, temp_config_file):
        """Test API key validation setting."""
        config = ConfigLoader(temp_config_file)
        assert config.should_validate_api_key_on_startup() is True

    def test_should_sanitize_error_messages(self, temp_config_file):
        """Test error message sanitization setting."""
        config = ConfigLoader(temp_config_file)
        assert config.should_sanitize_error_messages() is True

    def test_should_log_sensitive_data(self, temp_config_file):
        """Test sensitive data logging setting."""
        config = ConfigLoader(temp_config_file)
        assert config.should_log_sensitive_data() is False


@pytest.mark.unit
class TestFeatureFlags:
    """Test suite for feature flag methods."""

    def test_is_batch_processing_enabled(self, temp_config_file):
        """Test batch processing feature flag."""
        config = ConfigLoader(temp_config_file)
        assert config.is_batch_processing_enabled() is False

    def test_is_custom_rules_enabled(self, temp_config_file):
        """Test custom rules feature flag."""
        config = ConfigLoader(temp_config_file)
        assert config.is_custom_rules_enabled() is False

    def test_is_export_results_enabled(self, temp_config_file):
        """Test export results feature flag."""
        config = ConfigLoader(temp_config_file)
        assert config.is_export_results_enabled() is True

    def test_is_api_mode_enabled(self, temp_config_file):
        """Test API mode feature flag."""
        config = ConfigLoader(temp_config_file)
        assert config.is_api_mode_enabled() is False


@pytest.mark.unit
class TestDefaultValues:
    """Test suite for default values when config keys are missing."""

    def test_missing_ollama_model_name_default(self, tmp_path):
        """Test default Ollama model name when not in config."""
        minimal_config = tmp_path / "minimal.yaml"
        minimal_config.write_text("models: {}")

        config = ConfigLoader(str(minimal_config))
        assert config.get_ollama_model_name() == "llama3.2:latest"

    def test_missing_retry_config_default(self, tmp_path):
        """Test default retry config when not in config."""
        minimal_config = tmp_path / "minimal.yaml"
        minimal_config.write_text("logging: {}")

        config = ConfigLoader(str(minimal_config))
        retry_config = config.get_retry_config()

        assert retry_config['max_attempts'] == 3
        assert retry_config['min_wait'] == 2
        assert retry_config['max_wait'] == 10
