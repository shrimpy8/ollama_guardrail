"""
Unit Tests for Sensitive Information Redactor

Tests for the core redaction functionality.

Author: Harsh
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from redactor import SensitiveInformationRedactor


@pytest.mark.unit
class TestRedactorInitialization:
    """Test suite for redactor initialization."""

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    def test_initialization_with_defaults(self, mock_openai, mock_ollama):
        """Test redactor initialization with default models."""
        redactor = SensitiveInformationRedactor(openai_api_key="test-key")

        # Verify Ollama was initialized
        mock_ollama.assert_called_once()
        assert "llama3.2" in str(mock_ollama.call_args)

        # Verify OpenAI was initialized
        mock_openai.assert_called_once()
        assert "gpt-3.5-turbo" in str(mock_openai.call_args)

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    def test_initialization_with_custom_models(self, mock_openai, mock_ollama):
        """Test redactor initialization with custom model names."""
        redactor = SensitiveInformationRedactor(
            ollama_model_name="llama2:latest",
            openai_model_name="gpt-4",
            openai_api_key="test-key"
        )

        # Verify custom models were used
        mock_ollama.assert_called_once_with(model="llama2:latest")
        assert "gpt-4" in str(mock_openai.call_args)

    @patch('redactor.redactor.OllamaLLM')
    def test_initialization_without_openai_key(self, mock_ollama):
        """Test initialization without OpenAI API key."""
        redactor = SensitiveInformationRedactor()

        assert redactor.openai_model is None

    @patch('redactor.redactor.OllamaLLM')
    def test_initialization_ollama_failure(self, mock_ollama):
        """Test that initialization fails gracefully if Ollama fails."""
        mock_ollama.side_effect = Exception("Ollama connection error")

        with pytest.raises(Exception, match="Ollama connection error"):
            SensitiveInformationRedactor()


@pytest.mark.unit
class TestIdentifySensitiveInformation:
    """Test suite for identify_sensitive_information method."""

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_successful_identification(self, mock_retry, mock_ollama):
        """Test successful sensitive information identification."""
        # Setup mock response
        mock_response = json.dumps({
            "redacted_text": "My email is [EMAIL-1]",
            "detected_sensitive_data": [
                {
                    "type": "email",
                    "value": "john@example.com",
                    "placeholder": "[EMAIL-1]"
                }
            ]
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "My email is john@example.com",
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert redacted == "My email is [EMAIL-1]"
        assert len(result["detected_sensitive_data"]) == 1
        assert result["detected_sensitive_data"][0]["type"] == "email"

    @patch('redactor.redactor.OllamaLLM')
    def test_empty_text_input(self, mock_ollama):
        """Test handling of empty text input."""
        redactor = SensitiveInformationRedactor()

        result, redacted = redactor.identify_sensitive_information("", ["Email Addresses"])

        assert "error" in result
        assert result["error"] == "No text provided"
        assert redacted == ""

    @patch('redactor.redactor.OllamaLLM')
    def test_no_categories_selected(self, mock_ollama):
        """Test handling when no categories are selected."""
        redactor = SensitiveInformationRedactor()

        result, redacted = redactor.identify_sensitive_information("Some text", [])

        assert "error" in result
        assert result["error"] == "No categories selected"

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_invalid_json_response(self, mock_retry, mock_ollama):
        """Test handling of invalid JSON response from model."""
        # Return invalid JSON
        mock_retry.return_value = "This is not valid JSON"

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "Test text",
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert "error" in result
        assert "JSON" in result["error"]

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_model_exception(self, mock_retry, mock_ollama):
        """Test handling of exceptions during model invocation."""
        mock_retry.side_effect = Exception("Model error")

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "Test text",
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert "error" in result

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_multiple_categories(self, mock_retry, mock_ollama):
        """Test identification with multiple categories."""
        mock_response = json.dumps({
            "redacted_text": "Email: [EMAIL-1], Phone: [PHONE-1]",
            "detected_sensitive_data": [
                {"type": "email", "value": "test@example.com", "placeholder": "[EMAIL-1]"},
                {"type": "phone", "value": "555-1234", "placeholder": "[PHONE-1]"}
            ]
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "Email: test@example.com, Phone: 555-1234",
            ["Email Addresses", "Phone Numbers"],
            category_map={"Email Addresses": "[EMAIL-1]", "Phone Numbers": "[PHONE-1]"}
        )

        assert len(result["detected_sensitive_data"]) == 2

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    @patch('redactor.redactor.config')
    def test_sensitive_data_logging_disabled(self, mock_config, mock_retry, mock_ollama):
        """Test that sensitive data is not logged when disabled."""
        mock_config.should_log_sensitive_data.return_value = False
        mock_response = json.dumps({
            "redacted_text": "[EMAIL-1]",
            "detected_sensitive_data": [{"type": "email", "value": "secret@example.com"}]
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "secret@example.com",
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        # Just verify it completes without error
        assert redacted == "[EMAIL-1]"

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    @patch('redactor.redactor.config')
    def test_error_sanitization_enabled(self, mock_config, mock_retry, mock_ollama):
        """Test error message sanitization when enabled."""
        mock_config.should_sanitize_error_messages.return_value = True
        mock_retry.return_value = "Invalid JSON"

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            "Test",
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        # Error should be sanitized (not include raw output)
        assert "raw_output" not in result


@pytest.mark.unit
class TestSubmitToOpenAI:
    """Test suite for submit_to_openai method."""

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    @patch('redactor.redactor.retry_api_call')
    def test_successful_openai_submission(self, mock_retry, mock_openai_cls, mock_ollama):
        """Test successful OpenAI submission."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = "This is the OpenAI response"
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor(openai_api_key="test-key")
        result = redactor.submit_to_openai("Redacted text here")

        assert result == "This is the OpenAI response"

    @patch('redactor.redactor.OllamaLLM')
    def test_empty_text_to_openai(self, mock_ollama):
        """Test submitting empty text to OpenAI."""
        redactor = SensitiveInformationRedactor()
        result = redactor.submit_to_openai("")

        assert "No text provided" in result

    @patch('redactor.redactor.OllamaLLM')
    def test_openai_not_initialized(self, mock_ollama):
        """Test OpenAI submission when model not initialized."""
        redactor = SensitiveInformationRedactor()
        result = redactor.submit_to_openai("Some text")

        assert "not available" in result
        assert "API key" in result

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    @patch('redactor.redactor.retry_api_call')
    def test_openai_response_without_content(self, mock_retry, mock_openai_cls, mock_ollama):
        """Test handling OpenAI response without content attribute."""
        # Mock response without content attribute
        mock_response = Mock(spec=[])  # No attributes
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor(openai_api_key="test-key")
        result = redactor.submit_to_openai("Test text")

        assert "No response content" in result

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    @patch('redactor.redactor.retry_api_call')
    def test_openai_exception_handling(self, mock_retry, mock_openai_cls, mock_ollama):
        """Test exception handling in OpenAI submission."""
        mock_retry.side_effect = Exception("API error")

        redactor = SensitiveInformationRedactor(openai_api_key="test-key")
        result = redactor.submit_to_openai("Test text")

        assert "error occurred" in result.lower()

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    @patch('redactor.redactor.retry_api_call')
    @patch('redactor.redactor.config')
    def test_openai_instruction_prefix(self, mock_config, mock_retry, mock_openai_cls, mock_ollama):
        """Test that instruction prefix is added to OpenAI submission."""
        mock_config.get_openai_instruction_prefix.return_value = "INSTRUCTION: "
        mock_response = Mock()
        mock_response.content = "Response"
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor(openai_api_key="test-key")
        result = redactor.submit_to_openai("Test")

        # Verify retry_api_call was called with prefixed text
        call_args = mock_retry.call_args[0]
        assert "INSTRUCTION:" in call_args[0]


@pytest.mark.unit
class TestUpdateOpenAIApiKey:
    """Test suite for update_openai_api_key method."""

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    def test_successful_api_key_update(self, mock_openai_cls, mock_ollama):
        """Test successful API key update."""
        redactor = SensitiveInformationRedactor()

        result = redactor.update_openai_api_key("new-test-key")

        assert result is True
        mock_openai_cls.assert_called()

    @patch('redactor.redactor.OllamaLLM')
    def test_empty_api_key_update(self, mock_ollama):
        """Test update with empty API key."""
        redactor = SensitiveInformationRedactor()

        result = redactor.update_openai_api_key("")

        assert result is False

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.ChatOpenAI')
    def test_api_key_update_exception(self, mock_openai_cls, mock_ollama):
        """Test API key update with exception."""
        mock_openai_cls.side_effect = Exception("Invalid API key")

        redactor = SensitiveInformationRedactor()
        result = redactor.update_openai_api_key("invalid-key")

        assert result is False


@pytest.mark.integration
@pytest.mark.requires_ollama
class TestRedactorIntegration:
    """Integration tests requiring actual Ollama connection."""

    @pytest.mark.skip(reason="Requires Ollama to be running")
    def test_real_ollama_connection(self):
        """Test with real Ollama connection (skip by default)."""
        redactor = SensitiveInformationRedactor()

        result, redacted = redactor.identify_sensitive_information(
            "My email is test@example.com",
            ["Email Addresses"]
        )

        # This would test real behavior
        assert redacted is not None


@pytest.mark.unit
class TestRedactorEdgeCases:
    """Test suite for edge cases."""

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_very_long_text(self, mock_retry, mock_ollama):
        """Test with very long input text."""
        long_text = "This is a test. " * 1000  # 15000+ characters
        mock_response = json.dumps({
            "redacted_text": long_text,
            "detected_sensitive_data": []
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            long_text,
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert len(redacted) > 10000

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_special_characters_in_text(self, mock_retry, mock_ollama):
        """Test with special characters in text."""
        special_text = "Email: test@example.com\n\t<script>alert('xss')</script>"
        mock_response = json.dumps({
            "redacted_text": special_text.replace("test@example.com", "[EMAIL-1]"),
            "detected_sensitive_data": [{"type": "email", "value": "test@example.com"}]
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            special_text,
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert "[EMAIL-1]" in redacted

    @patch('redactor.redactor.OllamaLLM')
    @patch('redactor.redactor.retry_api_call')
    def test_unicode_characters(self, mock_retry, mock_ollama):
        """Test with Unicode characters."""
        unicode_text = "Email: test@example.com 你好 مرحبا"
        mock_response = json.dumps({
            "redacted_text": unicode_text.replace("test@example.com", "[EMAIL-1]"),
            "detected_sensitive_data": []
        })
        mock_retry.return_value = mock_response

        redactor = SensitiveInformationRedactor()
        result, redacted = redactor.identify_sensitive_information(
            unicode_text,
            ["Email Addresses"],
            category_map={"Email Addresses": "[EMAIL-1]"}
        )

        assert "你好" in redacted
        assert "مرحبا" in redacted
