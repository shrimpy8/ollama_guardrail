"""
Rate Limiter for Ollama Guardrail

Provides rate limiting functionality to prevent API quota exhaustion.
Uses token bucket algorithm for smooth rate limiting.

Author: Harsh
"""

import logging
import time
from typing import Callable, Any
from functools import wraps
from ratelimit import limits, sleep_and_retry

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API calls using token bucket algorithm.

    Attributes:
        max_requests_per_minute: Maximum requests allowed per minute
        max_tokens_per_minute: Maximum tokens allowed per minute (for OpenAI)

    Example:
        >>> limiter = RateLimiter(max_requests_per_minute=60)
        >>> @limiter.limit_requests
        >>> def my_api_call():
        >>>     return client.invoke(prompt)
    """

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_tokens_per_minute: int = 90000
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests per minute
            max_tokens_per_minute: Maximum tokens per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute
        self.request_count = 0
        self.token_count = 0
        self.window_start = time.time()

        logger.info(f"Rate limiter initialized: {max_requests_per_minute} req/min, {max_tokens_per_minute} tokens/min")

    def _reset_if_needed(self):
        """Reset counters if window has elapsed."""
        current_time = time.time()
        elapsed = current_time - self.window_start

        if elapsed >= 60:  # 1 minute window
            self.request_count = 0
            self.token_count = 0
            self.window_start = current_time
            logger.debug("Rate limiter window reset")

    def check_request_limit(self) -> bool:
        """
        Check if request can proceed without exceeding rate limit.

        Returns:
            True if request can proceed, False otherwise
        """
        self._reset_if_needed()

        if self.request_count >= self.max_requests_per_minute:
            logger.warning(f"Request rate limit exceeded: {self.request_count}/{self.max_requests_per_minute}")
            return False

        return True

    def check_token_limit(self, tokens: int) -> bool:
        """
        Check if request with given token count can proceed.

        Args:
            tokens: Number of tokens in the request

        Returns:
            True if request can proceed, False otherwise
        """
        self._reset_if_needed()

        if self.token_count + tokens > self.max_tokens_per_minute:
            logger.warning(f"Token rate limit would be exceeded: {self.token_count + tokens}/{self.max_tokens_per_minute}")
            return False

        return True

    def record_request(self, tokens: int = 0):
        """
        Record a successful API request.

        Args:
            tokens: Number of tokens used in the request
        """
        self.request_count += 1
        self.token_count += tokens
        logger.debug(f"Request recorded: {self.request_count} requests, {self.token_count} tokens")

    def wait_if_needed(self):
        """Wait until rate limit allows next request."""
        self._reset_if_needed()

        if not self.check_request_limit():
            # Calculate wait time until next window
            elapsed = time.time() - self.window_start
            wait_time = 60 - elapsed

            logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            self._reset_if_needed()

    def limit_requests(self, func: Callable) -> Callable:
        """
        Decorator to rate limit function calls.

        Args:
            func: Function to rate limit

        Returns:
            Wrapped function with rate limiting

        Example:
            >>> limiter = RateLimiter(max_requests_per_minute=60)
            >>> @limiter.limit_requests
            >>> def my_api_call():
            >>>     return client.invoke(prompt)
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Wait if necessary
            self.wait_if_needed()

            # Execute function
            try:
                result = func(*args, **kwargs)
                self.record_request()
                return result
            except Exception as e:
                logger.error(f"Rate-limited function failed: {str(e)}")
                raise

        return wrapper


# Global rate limiter instance (can be configured from config)
_global_limiter: RateLimiter = None


def init_global_rate_limiter(
    max_requests_per_minute: int = 60,
    max_tokens_per_minute: int = 90000
):
    """
    Initialize global rate limiter.

    Args:
        max_requests_per_minute: Maximum requests per minute
        max_tokens_per_minute: Maximum tokens per minute
    """
    global _global_limiter
    _global_limiter = RateLimiter(
        max_requests_per_minute=max_requests_per_minute,
        max_tokens_per_minute=max_tokens_per_minute
    )
    logger.info("Global rate limiter initialized")


def get_global_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance.

    Returns:
        Global RateLimiter instance

    Raises:
        RuntimeError: If rate limiter not initialized
    """
    if _global_limiter is None:
        raise RuntimeError("Global rate limiter not initialized. Call init_global_rate_limiter() first.")
    return _global_limiter


# Simple decorator using ratelimit library for ease of use
def rate_limited(max_calls: int = 60, period: int = 60):
    """
    Simple rate limiting decorator using ratelimit library.

    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds

    Returns:
        Decorated function with rate limiting

    Example:
        >>> @rate_limited(max_calls=60, period=60)
        >>> def my_api_call():
        >>>     return client.invoke(prompt)
    """
    def decorator(func):
        @sleep_and_retry
        @limits(calls=max_calls, period=period)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
