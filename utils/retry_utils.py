"""
Retry Utilities for Ollama Guardrail

Provides retry decorators and functions for API calls with exponential backoff.
Handles network errors, timeouts, and API errors gracefully.

Author: Harsh
"""

import logging
from typing import Any, Callable
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10,
    multiplier: int = 2
):
    """
    Create a retry decorator with exponential backoff for API operations.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Multiplier for exponential backoff

    Returns:
        Retry decorator configured with specified parameters

    Example:
        >>> @create_retry_decorator(max_attempts=3)
        >>> def my_api_call():
        >>>     return client.invoke(prompt)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((
            Exception,  # Retry on all exceptions for now
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def retry_api_call(
    func: Callable,
    *args,
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10,
    **kwargs
) -> Any:
    """
    Execute an API call with automatic retry logic.

    Uses exponential backoff strategy to handle temporary issues:
    - Attempt 1: Immediate
    - Attempt 2: Wait min_wait seconds
    - Attempt 3: Wait min_wait * multiplier seconds
    - Maximum wait: max_wait seconds

    Args:
        func: Function to call
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function call

    Raises:
        Exception: If function fails after all retries

    Example:
        >>> result = retry_api_call(
        >>>     ollama_model.invoke,
        >>>     prompt,
        >>>     max_attempts=3
        >>> )
    """
    logger.info(f"Executing API call with retry protection: {func.__name__}")

    decorator = create_retry_decorator(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait
    )

    @decorator
    def wrapped_func():
        return func(*args, **kwargs)

    try:
        result = wrapped_func()
        logger.info(f"API call successful: {func.__name__}")
        return result
    except Exception as e:
        logger.error(f"API call failed after {max_attempts} attempts: {str(e)}")
        raise


def safe_api_call(
    func: Callable,
    *args,
    fallback_value: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """
    Safely call an API function with error handling and optional fallback.

    Wraps API calls to catch and log exceptions, returning a fallback value
    instead of crashing the application.

    Args:
        func: The function to call
        *args: Positional arguments for the function
        fallback_value: Value to return if the function fails
        log_errors: Whether to log errors (default: True)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function call, or fallback_value on error

    Example:
        >>> result = safe_api_call(
        >>>     ollama_model.invoke,
        >>>     prompt,
        >>>     fallback_value={"error": "Service unavailable"}
        >>> )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"API call failed: {str(e)}", exc_info=True)
        return fallback_value


# Pre-configured retry decorator with standard settings
# Use this for most API calls
standard_retry = create_retry_decorator(
    max_attempts=3,
    min_wait=2,
    max_wait=10,
    multiplier=2
)
