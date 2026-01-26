# Configuration Reference

This document summarizes the main configuration options in `config.yaml`.

## Models
- `models.ollama.name`: Ollama model name (default: `llama3.2:latest`)
- `models.ollama.timeout`: Ollama timeout in seconds
- `models.openai.name`: OpenAI model name
- `models.openai.timeout`: OpenAI timeout in seconds
- `models.openai.temperature`: OpenAI temperature
- `models.openai.max_tokens`: OpenAI max tokens

## Retry
- `retry.max_attempts`: Maximum retry attempts
- `retry.min_wait`: Minimum wait time (seconds)
- `retry.max_wait`: Maximum wait time (seconds)
- `retry.multiplier`: Exponential backoff multiplier

## Rate Limiting
- `rate_limiting.enabled`: Enable/disable rate limiting
- `rate_limiting.max_requests_per_minute`: Request limit per minute
- `rate_limiting.max_tokens_per_minute`: Token limit per minute

## Logging
- `logging.level`: Log level (INFO/DEBUG/etc.)
- `logging.file`: Log file path
- `logging.console`: Enable console logging
- `logging.file_logging`: Enable file logging

## UI
- `ui.title`: Application title
- `ui.description`: UI description
- `ui.theme`: Theme name (`default`, `soft`, `monochrome`)
- `ui.share`: Enable Gradio share link
- `ui.server.host`: Server host
- `ui.server.port`: Server port
- `ui.components.input_text.soft_limit`: Soft character limit (warning)
- `ui.components.input_text.hard_limit`: Hard character limit (block)

## Prompts
- `prompts.redaction_template`: Path to prompt template
- `prompts.version`: Prompt version label

## Security
- `security.validate_api_key_on_startup`: Validate API key on startup
- `security.sanitize_error_messages`: Sanitize errors shown to users
- `security.log_sensitive_data`: Log detected sensitive data

## Feature Flags
Feature flags are present for planned capabilities. See `README.md` for current status.
