"""
Sensitive Information Redactor

Core redaction functionality for detecting and redacting sensitive information
from text using Ollama LLM for detection and OpenAI for optional processing.

This module provides production-ready redaction with:
- Retry logic with exponential backoff
- Rate limiting for API calls
- Comprehensive error handling
- Configurable detection categories

Author: Harsh
"""

import os
import json
import logging
import re
import inspect
from typing import List, Dict, Tuple, Optional, Any

from langchain_ollama.llms import OllamaLLM
from langchain_openai import ChatOpenAI

from utils import retry_api_call, load_config, get_global_rate_limiter
import prompt

logger = logging.getLogger(__name__)
config = load_config()


class SensitiveInformationRedactor:
    """
    A class to handle the redaction of sensitive information using LLM models.

    This class provides methods to:
    - Detect sensitive information in text using Ollama
    - Redact detected information with placeholders
    - Process redacted text with OpenAI

    All operations include retry logic, rate limiting, and comprehensive error handling.

    Attributes:
        ollama_model (OllamaLLM): Ollama model for sensitive information detection
        openai_model (ChatOpenAI): OpenAI model for processing redacted text (optional)

    Example:
        >>> redactor = SensitiveInformationRedactor()
        >>> result, redacted = redactor.identify_sensitive_information(
        ...     "My email is john@example.com",
        ...     ["Email Addresses"]
        ... )
        >>> print(redacted)
        "My email is [EMAIL-1]"
    """

    def __init__(
        self,
        ollama_model_name: Optional[str] = None,
        openai_model_name: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the redactor with specified LLM models.

        Args:
            ollama_model_name: Name of the Ollama model (uses config default if None)
            openai_model_name: Name of the OpenAI model (uses config default if None)
            openai_api_key: OpenAI API key (uses environment variable if None)

        Raises:
            Exception: If model initialization fails
        """
        # Use config defaults if not specified
        ollama_model_name = ollama_model_name or config.get_ollama_model_name()
        openai_model_name = openai_model_name or config.get_openai_model_name()

        # Get API key from parameter or environment
        if openai_api_key is None:
            openai_api_key = os.getenv("OPENAI_API_KEY", "")

        try:
            # Initialize Ollama model (request JSON format when supported)
            ollama_kwargs = {"model": ollama_model_name}
            try:
                if "format" in inspect.signature(OllamaLLM).parameters:
                    ollama_kwargs["format"] = "json"
            except (ValueError, TypeError):
                pass

            self.ollama_model = OllamaLLM(**ollama_kwargs)
            logger.info(f"Initialized Ollama model: {ollama_model_name}")

            # Initialize OpenAI model if API key is available
            if openai_api_key:
                self.openai_model = ChatOpenAI(
                    model=openai_model_name,
                    api_key=openai_api_key,
                    temperature=config.get_openai_temperature(),
                    max_tokens=config.get_openai_max_tokens(),
                    timeout=config.get_openai_timeout()
                )
                logger.info(f"Initialized OpenAI model: {openai_model_name}")
            else:
                self.openai_model = None
                logger.warning("OpenAI model not initialized due to missing API key")

        except Exception as e:
            logger.error(f"Error initializing models: {str(e)}")
            raise

    def identify_sensitive_information(
        self,
        text: str,
        categories: List[str],
        category_map: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict, str]:
        """
        Process input text to identify and redact sensitive information.

        This method uses the Ollama model to detect sensitive information based
        on selected categories and returns both detailed JSON output and redacted text.

        Args:
            text: Input text to analyze for sensitive information
            categories: List of category names to detect and redact
            category_map: Mapping of category names to placeholder patterns (uses config default if None)

        Returns:
            Tuple of (JSON output dict, redacted text string)

        Raises:
            None - All exceptions are caught and returned as error dicts

        Example:
            >>> redactor = SensitiveInformationRedactor()
            >>> result, redacted = redactor.identify_sensitive_information(
            >>>     "My email is john@example.com",
            >>>     ["Email Addresses"]
            >>> )
        """
        # Use config default if category_map not provided
        if category_map is None:
            category_map = config.get_category_map()

        # Track injection patterns without changing behavior
        injection_warnings = self._detect_prompt_injection(text)

        # Input validation
        if not text:
            logger.warning("Empty text provided for sensitive information detection")
            return {"error": "No text provided"}, ""

        if not categories:
            logger.warning("No categories selected for redaction")
            return {"error": "No categories selected"}, text

        try:
            # Build category prompt with names, placeholders, and descriptions
            categories_str, placeholder_templates = self._build_category_prompt(categories, category_map)

            # Format the prompt template with user text and selected categories
            template = prompt.get_template(config.get_prompt_template_path())
            formatted_prompt = template.format(
                category_selected=categories_str,
                user_prompt=text
            )

            logger.info(f"Processing text for {len(categories)} categories")
            logger.debug(f"Categories: {categories}")

            # Call the Ollama model with retry logic
            retry_config = config.get_retry_config()
            self._apply_rate_limit(prompt_text=formatted_prompt)
            output = retry_api_call(
                self.ollama_model.invoke,
                formatted_prompt,
                max_attempts=retry_config['max_attempts'],
                min_wait=retry_config['min_wait'],
                max_wait=retry_config['max_wait'],
                multiplier=retry_config.get('multiplier', 2)
            )

            logger.debug(f"Raw Ollama output: {output[:200]}...")  # Log first 200 chars

            # Parse JSON output from the model
            try:
                parsed_output = json.loads(output)
                parsed_output = self._normalize_output_schema(parsed_output, injection_warnings)
                if not self._validate_output_schema(parsed_output):
                    logger.error("Model output failed schema validation")
                    if config.should_sanitize_error_messages():
                        return {"error": "Invalid model output schema."}, ""
                    return {"error": "Invalid model output schema.", "raw_output": parsed_output}, ""
                redacted_text = parsed_output.get("redacted_text", "")
                detected_items = parsed_output.get('detected_sensitive_data', [])
                detected_count = len(detected_items)

                logger.info(f"Successfully parsed model output, detected {detected_count} sensitive items")

                # Log sensitive data only if configured to do so (WARNING: disable for production)
                if config.should_log_sensitive_data():
                    logger.debug(f"Detected sensitive data: {parsed_output.get('detected_sensitive_data', [])}")

                # Deterministic post-processing to ensure stable placeholders
                deterministic_redacted = self._deterministic_redaction(
                    text,
                    detected_items,
                    placeholder_templates
                )
                if deterministic_redacted is not None:
                    parsed_output["redacted_text"] = deterministic_redacted
                    redacted_text = deterministic_redacted

                return parsed_output, redacted_text

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse model output as JSON: {str(e)}")
                if config.should_log_sensitive_data():
                    logger.debug(f"Raw output: {output}")

                extracted = self._extract_json_from_output(output)
                if extracted is not None:
                    logger.info("Recovered JSON object from non-JSON model output")
                    parsed_output = self._normalize_output_schema(extracted, injection_warnings)
                    if not self._validate_output_schema(parsed_output):
                        logger.error("Model output failed schema validation")
                        if config.should_sanitize_error_messages():
                            return {"error": "Invalid model output schema."}, ""
                        return {"error": "Invalid model output schema.", "raw_output": parsed_output}, ""

                    redacted_text = parsed_output.get("redacted_text", "")
                    detected_items = parsed_output.get('detected_sensitive_data', [])
                    detected_count = len(detected_items)

                    logger.info(f"Successfully parsed model output, detected {detected_count} sensitive items")

                    if config.should_log_sensitive_data():
                        logger.debug(f"Detected sensitive data: {parsed_output.get('detected_sensitive_data', [])}")

                    deterministic_redacted = self._deterministic_redaction(
                        text,
                        detected_items,
                        placeholder_templates
                    )
                    if deterministic_redacted is not None:
                        parsed_output["redacted_text"] = deterministic_redacted
                        redacted_text = deterministic_redacted

                    return parsed_output, redacted_text

                error_msg = "Failed to parse output as JSON. The model may not have produced valid JSON format."
                if config.should_sanitize_error_messages():
                    # Return sanitized error for security
                    return {"error": error_msg}, ""
                else:
                    # Return detailed error for debugging
                    return {"error": error_msg, "raw_output": output}, ""

        except Exception as e:
            logger.error(f"Error in sensitive information detection: {str(e)}", exc_info=True)

            error_msg = "An error occurred during sensitive information detection."
            if config.should_sanitize_error_messages():
                return {"error": error_msg}, ""
            else:
                return {"error": f"{error_msg} Details: {str(e)}"}, ""

    def submit_to_openai(self, redacted_text: str) -> str:
        """
        Submit redacted text to OpenAI for processing.

        Args:
            redacted_text: Redacted text to submit to OpenAI

        Returns:
            Response from OpenAI model or error message

        Raises:
            None - All exceptions are caught and returned as error strings

        Example:
            >>> redactor = SensitiveInformationRedactor()
            >>> response = redactor.submit_to_openai("My email is [EMAIL-1]")
        """
        # Input validation
        if not redacted_text:
            logger.warning("Empty text provided for OpenAI processing")
            return "No text provided for processing."

        _openai_hard_limit = 10000
        if len(redacted_text) > _openai_hard_limit:
            logger.warning(f"Input text too long for OpenAI submission: {len(redacted_text)} chars (max {_openai_hard_limit})")
            return f"Input text is too long for OpenAI processing. Please limit input to {_openai_hard_limit} characters."

        if not self.openai_model:
            logger.error("OpenAI model not available - missing API key")
            return "OpenAI processing is not available. Please add an API key in the OpenAI Config tab."

        try:
            # Prepare the instruction with redacted text
            instruction_prefix = config.get_openai_instruction_prefix()
            final_prompt = instruction_prefix + redacted_text

            logger.info("Submitting redacted text to OpenAI")
            logger.debug(f"Prompt length: {len(final_prompt)} characters")

            # Call the OpenAI model with retry logic
            retry_config = config.get_retry_config()
            self._apply_rate_limit(prompt_text=final_prompt)
            response = retry_api_call(
                self.openai_model.invoke,
                final_prompt,
                max_attempts=retry_config['max_attempts'],
                min_wait=retry_config['min_wait'],
                max_wait=retry_config['max_wait'],
                multiplier=retry_config.get('multiplier', 2)
            )

            # Extract content from response
            if hasattr(response, 'content'):
                logger.info("Successfully received response from OpenAI")
                logger.debug(f"Response length: {len(response.content)} characters")
                return response.content
            else:
                logger.warning("No content in OpenAI response")
                return "No response content available."

        except Exception as e:
            logger.error(f"Error in OpenAI processing: {str(e)}", exc_info=True)

            error_msg = "An error occurred while processing with OpenAI."
            if config.should_sanitize_error_messages():
                return error_msg
            else:
                return f"{error_msg} Details: {str(e)}"

    def update_openai_api_key(self, new_api_key: str) -> bool:
        """
        Update the OpenAI API key and reinitialize the model.

        Args:
            new_api_key: New OpenAI API key

        Returns:
            True if update successful, False otherwise

        Example:
            >>> redactor = SensitiveInformationRedactor()
            >>> success = redactor.update_openai_api_key("sk-...")
        """
        try:
            if not new_api_key:
                logger.warning("Attempted to update with empty API key")
                return False

            # Update the OpenAI model
            self.openai_model = ChatOpenAI(
                model=config.get_openai_model_name(),
                api_key=new_api_key,
                temperature=config.get_openai_temperature(),
                max_tokens=config.get_openai_max_tokens(),
                timeout=config.get_openai_timeout()
            )
            logger.info("OpenAI model updated with new API key")
            return True

        except Exception as e:
            logger.error(f"Failed to update OpenAI model: {str(e)}")
            return False

    def _apply_rate_limit(self, prompt_text: str) -> None:
        """Apply config-driven rate limiting with token accounting.

        No-op if rate limiting is disabled or not initialized.

        Args:
            prompt_text (str): Prompt used to estimate tokens.
        """
        if not config.is_rate_limiting_enabled():
            return

        try:
            limiter = get_global_rate_limiter()
        except RuntimeError:
            logger.warning("Rate limiter not initialized; skipping rate limiting.")
            return

        tokens = self._estimate_tokens(prompt_text)
        limiter.wait_for_allowance(tokens=tokens)
        limiter.record_request(tokens=tokens)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken when available, else heuristic.

        Args:
            text (str): Input text to estimate.

        Returns:
            int: Estimated token count.
        """
        try:
            import tiktoken  # type: ignore
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Heuristic: ~4 chars/token
            return max(1, len(text) // 4)

    def _build_category_prompt(
        self,
        categories: List[str],
        category_map: Dict[str, str]
    ) -> Tuple[str, Dict[str, str]]:
        """Build category prompt lines and placeholder templates.

        Args:
            categories (List[str]): Selected category names.
            category_map (Dict[str, str]): Name -> placeholder map.

        Returns:
            Tuple[str, Dict[str, str]]: Prompt lines and placeholder templates.
        """
        enabled_categories = config.get_redaction_categories()
        if not isinstance(enabled_categories, list):
            enabled_categories = []
        enabled_by_name = {cat.get("name"): cat for cat in enabled_categories}

        placeholder_templates: Dict[str, str] = {}
        lines: List[str] = []
        for name in categories:
            cat = enabled_by_name.get(name)
            if cat:
                placeholder = cat.get("placeholder", "")
                description = cat.get("description", "")
            else:
                placeholder = category_map.get(name, "")
                description = ""

            placeholder_template = self._normalize_placeholder_template(placeholder)
            placeholder_templates[name] = placeholder_template

            if placeholder_template or description:
                line = f"- {name} | placeholder: {placeholder_template or placeholder} | {description}".strip()
            else:
                line = f"- {name}"
            lines.append(line)

        return "\n".join(lines), placeholder_templates

    def _normalize_placeholder_template(self, placeholder: str) -> str:
        """Ensure placeholder contains {index} for deterministic numbering.

        Args:
            placeholder (str): Placeholder text from config.

        Returns:
            str: Normalized template with {index} when possible.
        """
        if "{index}" in placeholder:
            return placeholder

        # Try to normalize common patterns like [EMAIL-1] -> [EMAIL-{index}]
        match = re.search(r"^(.*-)(\d+)(\])$", placeholder)
        if match:
            return f"{match.group(1)}{{index}}{match.group(3)}"

        return placeholder

    def _normalize_output_schema(self, parsed_output: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
        """Normalize output schema and attach warnings.

        Args:
            parsed_output (Dict[str, Any]): Raw parsed model output.
            warnings (List[str]): Warning messages to attach.

        Returns:
            Dict[str, Any]: Normalized output.
        """
        if "detected_sensitive_data" not in parsed_output or not isinstance(parsed_output["detected_sensitive_data"], list):
            parsed_output["detected_sensitive_data"] = []
        if "redacted_text" not in parsed_output or not isinstance(parsed_output["redacted_text"], str):
            parsed_output["redacted_text"] = ""
        if warnings:
            parsed_output.setdefault("warnings", [])
            parsed_output["warnings"].extend(warnings)
        return parsed_output

    def _validate_output_schema(self, parsed_output: Dict[str, Any]) -> bool:
        """Validate minimal output schema for safety.

        Args:
            parsed_output (Dict[str, Any]): Parsed model output.

        Returns:
            bool: True if schema is minimally valid.
        """
        items = parsed_output.get("detected_sensitive_data", [])
        if not isinstance(items, list):
            return False
        redacted_text = parsed_output.get("redacted_text", "")
        if not isinstance(redacted_text, str):
            return False
        if not items and redacted_text.strip() == "":
            return False
        for item in items:
            if not isinstance(item, dict):
                return False
            data = item.get("data") or item.get("value") or item.get("text")
            category = item.get("category") or item.get("label")
            if not isinstance(data, str) or not isinstance(category, str):
                return False
        return True

    def _detect_prompt_injection(self, text: str) -> List[str]:
        """Detect common prompt injection patterns for logging/warnings.

        Returns a warning list without changing behavior.

        Args:
            text (str): User input text.

        Returns:
            List[str]: Warning messages, if any.
        """
        patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+the\s+above",
            r"system\s+prompt",
            r"you\s+are\s+now",
            r"developer\s+message",
        ]
        warnings: List[str] = []
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                warnings.append("Potential prompt injection pattern detected.")
                break
        if warnings:
            logger.warning("Potential prompt injection pattern detected in input.")
        return warnings

    def _deterministic_redaction(
        self,
        original_text: str,
        detected_items: List[Dict[str, Any]],
        placeholder_templates: Dict[str, str]
    ) -> Optional[str]:
        """Apply deterministic redaction using detected items and templates.

        Returns None if required fields are missing.

        Args:
            original_text (str): Original user input.
            detected_items (List[Dict[str, Any]]): Model-detected items.
            placeholder_templates (Dict[str, str]): Category -> template mapping.

        Returns:
            Optional[str]: Redacted text, or None if data is incomplete.
        """
        placeholder_pattern = re.compile(r"^\[[A-Z0-9-]+-\d+\]$")
        normalized_items: List[Dict[str, str]] = []
        for item in detected_items:
            data = item.get("data") or item.get("value") or item.get("text")
            category = item.get("category") or item.get("label")
            if not data or not category:
                return None
            if isinstance(data, str) and placeholder_pattern.match(data):
                # Model returned a placeholder instead of the original text.
                return None
            template = placeholder_templates.get(category)
            if not template:
                return None
            normalized_items.append({"data": str(data), "category": str(category), "template": template})

        redacted_text = original_text
        counters: Dict[str, int] = {}
        for item in normalized_items:
            category = item["category"]
            counters[category] = counters.get(category, 0) + 1
            placeholder = item["template"].replace("{index}", str(counters[category]))
            # Replace first occurrence only to keep ordering stable
            redacted_text = re.sub(re.escape(item["data"]), placeholder, redacted_text, count=1)

        return redacted_text

    def _extract_json_from_output(self, output: str) -> Optional[Dict[str, Any]]:
        """Extract the first valid JSON object from a mixed-output string.

        Args:
            output (str): Model output that may include extra text.

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON object if found.
        """
        if not output:
            return None

        # Strip fenced code blocks if present.
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except Exception:
                pass

        # Scan for balanced JSON objects.
        starts = []
        candidates = []
        for i, ch in enumerate(output):
            if ch == "{":
                starts.append(i)
            elif ch == "}" and starts:
                start = starts.pop()
                if not starts:
                    candidates.append(output[start:i + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        return None
