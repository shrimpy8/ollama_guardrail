"""
Configuration Loader for Ollama Guardrail

Provides type-safe configuration management with YAML file support.
Uses singleton pattern for efficient configuration access throughout the application.

Author: Harsh
"""

import os
import logging
from typing import Dict, Any, Optional, List
import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Type-safe configuration loader for Ollama Guardrail.

    Loads configuration from config.yaml and provides typed access methods
    for various configuration sections.

    Attributes:
        config (Dict[str, Any]): The loaded configuration dictionary

    Example:
        >>> config = ConfigLoader()
        >>> ollama_model = config.get_ollama_model_name()
        >>> print(ollama_model)
        'llama3.2:latest'
    """

    _instance: Optional['ConfigLoader'] = None

    def __new__(cls, config_path: str = "config.yaml"):
        """Implement singleton pattern to avoid reloading config."""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the YAML configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)

            logger.info(f"Configuration loaded successfully from {config_path}")
            self._initialized = True

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise

    # Model Configuration Methods
    def get_ollama_model_name(self) -> str:
        """Get Ollama model name."""
        return self.config.get('models', {}).get('ollama', {}).get('name', 'llama3.2:latest')

    def get_ollama_timeout(self) -> int:
        """Get Ollama API timeout in seconds."""
        return self.config.get('models', {}).get('ollama', {}).get('timeout', 120)

    def get_openai_model_name(self) -> str:
        """Get OpenAI model name."""
        return self.config.get('models', {}).get('openai', {}).get('name', 'gpt-3.5-turbo')

    def get_openai_timeout(self) -> int:
        """Get OpenAI API timeout in seconds."""
        return self.config.get('models', {}).get('openai', {}).get('timeout', 60)

    def get_openai_temperature(self) -> float:
        """Get OpenAI temperature setting."""
        return self.config.get('models', {}).get('openai', {}).get('temperature', 0.7)

    def get_openai_max_tokens(self) -> int:
        """Get OpenAI max tokens."""
        return self.config.get('models', {}).get('openai', {}).get('max_tokens', 2000)

    # Retry Configuration Methods
    def get_retry_config(self) -> Dict[str, int]:
        """
        Get retry configuration for API calls.

        Returns:
            Dictionary with max_attempts, min_wait, max_wait, multiplier
        """
        return self.config.get('retry', {
            'max_attempts': 3,
            'min_wait': 2,
            'max_wait': 10,
            'multiplier': 2
        })

    def get_max_retry_attempts(self) -> int:
        """Get maximum retry attempts."""
        return self.get_retry_config().get('max_attempts', 3)

    # Rate Limiting Configuration Methods
    def is_rate_limiting_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self.config.get('rate_limiting', {}).get('enabled', True)

    def get_max_requests_per_minute(self) -> int:
        """Get maximum requests per minute."""
        return self.config.get('rate_limiting', {}).get('max_requests_per_minute', 60)

    def get_max_tokens_per_minute(self) -> int:
        """Get maximum tokens per minute."""
        return self.config.get('rate_limiting', {}).get('max_tokens_per_minute', 90000)

    # Logging Configuration Methods
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.

        Returns:
            Dictionary with level, format, file, console, file_logging, max_bytes, backup_count
        """
        return self.config.get('logging', {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'app.log',
            'console': True,
            'file_logging': True,
            'max_bytes': 10485760,
            'backup_count': 5
        })

    # UI Configuration Methods
    def get_ui_title(self) -> str:
        """Get Gradio interface title."""
        return self.config.get('ui', {}).get('title', 'Sensitive Information Redaction Tool')

    def get_ui_description(self) -> str:
        """Get Gradio interface description."""
        return self.config.get('ui', {}).get('description',
                                             'Identify and redact sensitive information from text before AI processing')

    def get_ui_theme(self) -> str:
        """Get Gradio theme."""
        return self.config.get('ui', {}).get('theme', 'default')

    def get_ui_share(self) -> bool:
        """Get whether to enable public sharing."""
        return self.config.get('ui', {}).get('share', False)

    def get_server_config(self) -> Dict[str, Any]:
        """
        Get server configuration.

        Returns:
            Dictionary with port and host
        """
        return self.config.get('ui', {}).get('server', {
            'port': 7860,
            'host': '127.0.0.1'
        })

    def get_input_text_config(self) -> Dict[str, Any]:
        """Get input text component configuration."""
        return self.config.get('ui', {}).get('components', {}).get('input_text', {
            'lines': 10,
            'placeholder': 'Enter text to analyze for sensitive information...'
        })

    def get_output_text_config(self) -> Dict[str, Any]:
        """Get output text component configuration."""
        return self.config.get('ui', {}).get('components', {}).get('output_text', {
            'lines': 10
        })

    def get_category_selection_default_all(self) -> bool:
        """Check if all categories should be selected by default."""
        return self.config.get('ui', {}).get('components', {}).get('category_selection', {}).get('default_all', False)

    # Redaction Categories Methods
    def get_redaction_categories(self) -> List[Dict[str, str]]:
        """
        Get enabled redaction categories.

        Returns:
            List of dictionaries with name, placeholder, description
        """
        return self.config.get('categories', {}).get('enabled', [])

    def get_category_map(self) -> Dict[str, str]:
        """
        Get mapping of category names to placeholders.

        Returns:
            Dictionary mapping category names to placeholder patterns
        """
        categories = self.get_redaction_categories()
        category_map = {}
        for category in categories:
            name = category.get('name')
            placeholder = category.get('placeholder', f"[{name.upper()}-{{index}}]")
            # Replace {index} with 1 for the map
            placeholder = placeholder.replace('{index}', '1')
            category_map[name] = placeholder
        return category_map

    def get_category_options(self) -> List[str]:
        """
        Get list of category names.

        Returns:
            List of category names
        """
        return [cat.get('name') for cat in self.get_redaction_categories()]

    # OpenAI Processing Configuration
    def get_openai_instruction_prefix(self) -> str:
        """Get instruction prefix for OpenAI processing."""
        return self.config.get('openai_processing', {}).get('instruction_prefix',
                                                              'The following text has been redacted for sensitive information. Please process the text as it is provided as a PROMPT:\n')

    def is_auto_submit_enabled(self) -> bool:
        """Check if automatic OpenAI submission is enabled."""
        return self.config.get('openai_processing', {}).get('enable_automatic_submit', False)

    # Security Configuration
    def should_validate_api_key_on_startup(self) -> bool:
        """Check if API key validation on startup is enabled."""
        return self.config.get('security', {}).get('validate_api_key_on_startup', True)

    def should_sanitize_error_messages(self) -> bool:
        """Check if error message sanitization is enabled."""
        return self.config.get('security', {}).get('sanitize_error_messages', True)

    def should_log_sensitive_data(self) -> bool:
        """Check if logging sensitive data is enabled (WARNING: disable for production)."""
        return self.config.get('security', {}).get('log_sensitive_data', False)

    # Feature Flags
    def is_batch_processing_enabled(self) -> bool:
        """Check if batch processing is enabled."""
        return self.config.get('features', {}).get('batch_processing', False)

    def is_custom_rules_enabled(self) -> bool:
        """Check if custom redaction rules are enabled."""
        return self.config.get('features', {}).get('custom_rules', False)

    def is_export_results_enabled(self) -> bool:
        """Check if exporting results is enabled."""
        return self.config.get('features', {}).get('export_results', True)

    def is_api_mode_enabled(self) -> bool:
        """Check if REST API mode is enabled."""
        return self.config.get('features', {}).get('api_mode', False)


# Convenience function for quick access
def load_config(config_path: str = "config.yaml") -> ConfigLoader:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        ConfigLoader instance

    Example:
        >>> config = load_config()
        >>> model = config.get_ollama_model_name()
    """
    return ConfigLoader(config_path)
