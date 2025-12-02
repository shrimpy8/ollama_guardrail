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
from typing import List, Dict, Tuple, Optional

from langchain_ollama.llms import OllamaLLM
from langchain_openai import ChatOpenAI

from utils import retry_api_call, rate_limited, load_config
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
            # Initialize Ollama model
            self.ollama_model = OllamaLLM(model=ollama_model_name)
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

    @rate_limited(max_calls=60, period=60)
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

        # Input validation
        if not text:
            logger.warning("Empty text provided for sensitive information detection")
            return {"error": "No text provided"}, ""

        if not categories:
            logger.warning("No categories selected for redaction")
            return {"error": "No categories selected"}, text

        try:
            # Get formatting for selected categories
            selected_formats = [category_map[cat] for cat in categories if cat in category_map]
            categories_str = "\n".join(selected_formats)

            # Format the prompt template with user text and selected categories
            formatted_prompt = prompt.template.format(
                category_selected=categories_str,
                user_prompt=text
            )

            logger.info(f"Processing text for {len(categories)} categories")
            logger.debug(f"Categories: {categories}")

            # Call the Ollama model with retry logic
            retry_config = config.get_retry_config()
            output = retry_api_call(
                self.ollama_model.invoke,
                formatted_prompt,
                max_attempts=retry_config['max_attempts'],
                min_wait=retry_config['min_wait'],
                max_wait=retry_config['max_wait']
            )

            logger.debug(f"Raw Ollama output: {output[:200]}...")  # Log first 200 chars

            # Parse JSON output from the model
            try:
                parsed_output = json.loads(output)
                redacted_text = parsed_output.get("redacted_text", "")
                detected_count = len(parsed_output.get('detected_sensitive_data', []))

                logger.info(f"Successfully parsed model output, detected {detected_count} sensitive items")

                # Log sensitive data only if configured to do so (WARNING: disable for production)
                if config.should_log_sensitive_data():
                    logger.debug(f"Detected sensitive data: {parsed_output.get('detected_sensitive_data', [])}")

                return parsed_output, redacted_text

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse model output as JSON: {str(e)}")
                logger.debug(f"Raw output: {output}")

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

    @rate_limited(max_calls=60, period=60)
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
            response = retry_api_call(
                self.openai_model.invoke,
                final_prompt,
                max_attempts=retry_config['max_attempts'],
                min_wait=retry_config['min_wait'],
                max_wait=retry_config['max_wait']
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
