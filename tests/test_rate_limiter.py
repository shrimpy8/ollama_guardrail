"""
Unit Tests for Rate Limiter

Tests for rate limiting functionality using token bucket algorithm.

Author: Harsh
"""

import pytest
import time
from unittest.mock import patch, Mock
from utils.rate_limiter import (
    RateLimiter,
    init_global_rate_limiter,
    get_global_rate_limiter,
    rate_limited
)


@pytest.mark.unit
class TestRateLimiter:
    """Test suite for RateLimiter class."""

    def test_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_requests_per_minute=100, max_tokens_per_minute=50000)

        assert limiter.max_requests_per_minute == 100
        assert limiter.max_tokens_per_minute == 50000
        assert limiter.request_count == 0
        assert limiter.token_count == 0

    def test_check_request_limit_within_limit(self):
        """Test check_request_limit when within limit."""
        limiter = RateLimiter(max_requests_per_minute=10)

        limiter.request_count = 5
        assert limiter.check_request_limit() is True

    def test_check_request_limit_at_limit(self):
        """Test check_request_limit when at limit."""
        limiter = RateLimiter(max_requests_per_minute=10)

        limiter.request_count = 10
        assert limiter.check_request_limit() is False

    def test_check_request_limit_exceeds_limit(self):
        """Test check_request_limit when exceeding limit."""
        limiter = RateLimiter(max_requests_per_minute=10)

        limiter.request_count = 15
        assert limiter.check_request_limit() is False

    def test_check_token_limit_within_limit(self):
        """Test check_token_limit when within limit."""
        limiter = RateLimiter(max_tokens_per_minute=1000)

        limiter.token_count = 500
        assert limiter.check_token_limit(400) is True

    def test_check_token_limit_would_exceed(self):
        """Test check_token_limit when would exceed limit."""
        limiter = RateLimiter(max_tokens_per_minute=1000)

        limiter.token_count = 800
        assert limiter.check_token_limit(300) is False

    def test_record_request(self):
        """Test record_request increments counters."""
        limiter = RateLimiter()

        limiter.record_request(tokens=100)

        assert limiter.request_count == 1
        assert limiter.token_count == 100

        limiter.record_request(tokens=50)

        assert limiter.request_count == 2
        assert limiter.token_count == 150

    def test_reset_if_needed_within_window(self):
        """Test that counters are not reset within time window."""
        limiter = RateLimiter()
        limiter.request_count = 5
        limiter.token_count = 100

        # Should not reset within 60 seconds
        limiter._reset_if_needed()

        assert limiter.request_count == 5
        assert limiter.token_count == 100

    def test_reset_if_needed_after_window(self):
        """Test that counters reset after time window."""
        limiter = RateLimiter()
        limiter.request_count = 5
        limiter.token_count = 100

        # Simulate time passing
        limiter.window_start = time.time() - 61  # 61 seconds ago

        limiter._reset_if_needed()

        assert limiter.request_count == 0
        assert limiter.token_count == 0

    @patch('time.sleep')
    def test_wait_if_needed_at_limit(self, mock_sleep):
        """Test wait_if_needed when at rate limit."""
        limiter = RateLimiter(max_requests_per_minute=10)
        limiter.request_count = 10
        limiter.window_start = time.time() - 30  # 30 seconds into window

        limiter.wait_if_needed()

        # Should have slept for approximately 30 seconds (60 - 30)
        assert mock_sleep.called
        sleep_time = mock_sleep.call_args[0][0]
        assert 25 < sleep_time < 35  # Allow some tolerance

    def test_wait_if_needed_within_limit(self):
        """Test wait_if_needed when within limit (should not wait)."""
        limiter = RateLimiter(max_requests_per_minute=10)
        limiter.request_count = 5

        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time

        # Should not have waited
        assert elapsed < 0.1

    def test_limit_requests_decorator_successful(self):
        """Test limit_requests decorator on successful function."""
        limiter = RateLimiter(max_requests_per_minute=100)
        mock_func = Mock(return_value="success")

        @limiter.limit_requests
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert limiter.request_count == 1
        mock_func.assert_called_once()

    def test_limit_requests_decorator_with_exception(self):
        """Test limit_requests decorator when function raises exception."""
        limiter = RateLimiter(max_requests_per_minute=100)
        mock_func = Mock(side_effect=Exception("Test error"))

        @limiter.limit_requests
        def test_func():
            return mock_func()

        with pytest.raises(Exception, match="Test error"):
            test_func()

        # Request should not be recorded on failure
        assert limiter.request_count == 0

    @patch('time.sleep')
    def test_limit_requests_decorator_rate_limited(self, mock_sleep):
        """Test limit_requests decorator enforces rate limit."""
        limiter = RateLimiter(max_requests_per_minute=2)
        call_count = []

        @limiter.limit_requests
        def test_func():
            call_count.append(1)
            return "success"

        # First two calls should succeed immediately
        test_func()
        test_func()

        assert len(call_count) == 2
        assert limiter.request_count == 2

        # Third call should trigger wait (but we've mocked sleep)
        limiter.window_start = time.time() - 30  # Simulate 30 seconds elapsed
        test_func()

        assert mock_sleep.called


@pytest.mark.unit
class TestGlobalRateLimiter:
    """Test suite for global rate limiter functions."""

    def test_init_global_rate_limiter(self):
        """Test initialization of global rate limiter."""
        init_global_rate_limiter(max_requests_per_minute=100, max_tokens_per_minute=50000)

        limiter = get_global_rate_limiter()

        assert isinstance(limiter, RateLimiter)
        assert limiter.max_requests_per_minute == 100
        assert limiter.max_tokens_per_minute == 50000

    def test_get_global_rate_limiter_not_initialized(self):
        """Test get_global_rate_limiter raises error when not initialized."""
        # Reset global limiter
        import utils.rate_limiter
        utils.rate_limiter._global_limiter = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_global_rate_limiter()

    def test_get_global_rate_limiter_after_init(self):
        """Test get_global_rate_limiter returns limiter after initialization."""
        init_global_rate_limiter(max_requests_per_minute=50)

        limiter1 = get_global_rate_limiter()
        limiter2 = get_global_rate_limiter()

        # Should return same instance
        assert limiter1 is limiter2


@pytest.mark.unit
class TestRateLimitedDecorator:
    """Test suite for rate_limited decorator."""

    @pytest.mark.slow
    def test_rate_limited_decorator_basic(self):
        """Test basic functionality of rate_limited decorator."""
        call_times = []

        @rate_limited(max_calls=2, period=1)
        def test_func():
            call_times.append(time.time())
            return "success"

        # First two calls should succeed quickly
        test_func()
        test_func()

        assert len(call_times) == 2
        # They should be very close together
        assert (call_times[1] - call_times[0]) < 0.1

    def test_rate_limited_decorator_with_args(self):
        """Test rate_limited decorator with function arguments."""
        @rate_limited(max_calls=10, period=1)
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_rate_limited_decorator_preserves_metadata(self):
        """Test that rate_limited decorator preserves function metadata."""
        @rate_limited(max_calls=10, period=1)
        def documented_func():
            """This function has documentation."""
            return "result"

        assert documented_func.__doc__ == "This function has documentation."
        assert documented_func.__name__ == "documented_func"


@pytest.mark.unit
class TestRateLimiterLogging:
    """Test suite for rate limiter logging."""

    @patch('utils.rate_limiter.logger')
    def test_initialization_logging(self, mock_logger):
        """Test that initialization is logged."""
        RateLimiter(max_requests_per_minute=60, max_tokens_per_minute=90000)

        mock_logger.info.assert_called_once()
        assert "60 req/min" in str(mock_logger.info.call_args)

    @patch('utils.rate_limiter.logger')
    def test_rate_limit_exceeded_logging(self, mock_logger):
        """Test that rate limit exceeded is logged."""
        limiter = RateLimiter(max_requests_per_minute=5)
        limiter.request_count = 10

        limiter.check_request_limit()

        # Should log warning about exceeded limit
        assert mock_logger.warning.called

    @patch('utils.rate_limiter.logger')
    def test_record_request_logging(self, mock_logger):
        """Test that request recording is logged at debug level."""
        limiter = RateLimiter()

        limiter.record_request(tokens=100)

        mock_logger.debug.assert_called_once()


@pytest.mark.unit
class TestRateLimiterEdgeCases:
    """Test suite for edge cases in rate limiting."""

    def test_zero_requests_per_minute(self):
        """Test behavior with zero requests per minute."""
        limiter = RateLimiter(max_requests_per_minute=0)

        # Should immediately fail limit check
        assert limiter.check_request_limit() is False

    def test_very_high_rate_limit(self):
        """Test with very high rate limit."""
        limiter = RateLimiter(max_requests_per_minute=1000000)

        # Should handle many requests
        for _ in range(1000):
            limiter.record_request()

        assert limiter.request_count == 1000
        assert limiter.check_request_limit() is True

    def test_negative_token_count(self):
        """Test behavior with negative token count (edge case)."""
        limiter = RateLimiter(max_tokens_per_minute=1000)

        # Even with negative current count, adding tokens should work
        limiter.token_count = -100
        assert limiter.check_token_limit(500) is True

    def test_rapid_sequential_calls(self):
        """Test many rapid sequential calls."""
        limiter = RateLimiter(max_requests_per_minute=100)

        for i in range(50):
            limiter.record_request(tokens=10)

        assert limiter.request_count == 50
        assert limiter.token_count == 500
        assert limiter.check_request_limit() is True

    def test_window_boundary_condition(self):
        """Test behavior exactly at window boundary."""
        limiter = RateLimiter(max_requests_per_minute=10)
        limiter.request_count = 5

        # Set window start to exactly 60 seconds ago
        limiter.window_start = time.time() - 60.0

        limiter._reset_if_needed()

        # Should have reset
        assert limiter.request_count == 0
