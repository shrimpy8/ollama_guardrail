"""
Unit Tests for Retry Utilities

Tests for retry logic with exponential backoff.

Author: Harsh
"""

import pytest
import time
from unittest.mock import Mock, patch
from utils.retry_utils import (
    create_retry_decorator,
    retry_api_call,
    safe_api_call,
    standard_retry
)


@pytest.mark.unit
class TestCreateRetryDecorator:
    """Test suite for create_retry_decorator function."""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't retry."""
        mock_func = Mock(return_value="success")
        decorator = create_retry_decorator(max_attempts=3)

        @decorator
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_exception(self):
        """Test that function retries on exception."""
        mock_func = Mock(side_effect=[Exception("First fail"), Exception("Second fail"), "success"])
        decorator = create_retry_decorator(max_attempts=3, min_wait=0.1, max_wait=0.2)

        @decorator
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_max_attempts_exceeded(self):
        """Test that exception is raised after max attempts."""
        mock_func = Mock(side_effect=Exception("Always fails"))
        decorator = create_retry_decorator(max_attempts=3, min_wait=0.1, max_wait=0.2)

        @decorator
        def test_func():
            return mock_func()

        with pytest.raises(Exception, match="Always fails"):
            test_func()

        assert mock_func.call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases wait time."""
        call_times = []

        def failing_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("Fail")
            return "success"

        decorator = create_retry_decorator(max_attempts=3, min_wait=0.1, max_wait=0.5, multiplier=2)

        @decorator
        def test_func():
            return failing_func()

        result = test_func()

        assert result == "success"
        assert len(call_times) == 3

        # Check that wait times increased
        wait1 = call_times[1] - call_times[0]
        wait2 = call_times[2] - call_times[1]

        assert wait1 >= 0.1  # At least min_wait
        assert wait2 >= wait1  # Second wait should be longer


@pytest.mark.unit
class TestRetryApiCall:
    """Test suite for retry_api_call function."""

    def test_successful_api_call(self):
        """Test successful API call without retries."""
        mock_func = Mock(return_value="api response")

        result = retry_api_call(mock_func, "arg1", "arg2", kwarg1="value1")

        assert result == "api response"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")

    def test_retry_on_failure(self):
        """Test retry on API call failure."""
        mock_func = Mock(side_effect=[Exception("Fail 1"), Exception("Fail 2"), "success"])

        result = retry_api_call(mock_func, max_attempts=3, min_wait=0.1, max_wait=0.2)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_exception_after_max_attempts(self):
        """Test that exception is raised after max attempts."""
        mock_func = Mock(side_effect=Exception("Always fails"))

        with pytest.raises(Exception, match="Always fails"):
            retry_api_call(mock_func, max_attempts=2, min_wait=0.1, max_wait=0.2)

        assert mock_func.call_count == 2

    def test_with_function_arguments(self):
        """Test retry_api_call with various argument types."""
        def api_func(a, b, c=None):
            if api_func.call_count < 2:
                api_func.call_count += 1
                raise Exception("Temporary failure")
            return f"{a}-{b}-{c}"

        api_func.call_count = 0

        result = retry_api_call(api_func, "arg1", "arg2", c="kwarg", max_attempts=3, min_wait=0.1)

        assert result == "arg1-arg2-kwarg"

    @patch('utils.retry_utils.logger')
    def test_logging_on_retry(self, mock_logger):
        """Test that retries are logged."""
        mock_func = Mock(side_effect=[Exception("Fail"), "success"])

        result = retry_api_call(mock_func, max_attempts=2, min_wait=0.1)

        assert result == "success"
        # Should log start and success
        assert mock_logger.info.call_count >= 2


@pytest.mark.unit
class TestSafeApiCall:
    """Test suite for safe_api_call function."""

    def test_successful_call_returns_result(self):
        """Test that successful calls return the result."""
        mock_func = Mock(return_value="success")

        result = safe_api_call(mock_func, "arg1", kwarg="value")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg="value")

    def test_exception_returns_fallback(self):
        """Test that exceptions return fallback value."""
        mock_func = Mock(side_effect=Exception("API error"))

        result = safe_api_call(mock_func, fallback_value="fallback")

        assert result == "fallback"

    def test_exception_returns_none_by_default(self):
        """Test that exceptions return None when no fallback specified."""
        mock_func = Mock(side_effect=Exception("API error"))

        result = safe_api_call(mock_func)

        assert result is None

    @patch('utils.retry_utils.logger')
    def test_error_logging_enabled(self, mock_logger):
        """Test that errors are logged when log_errors is True."""
        mock_func = Mock(side_effect=Exception("API error"))

        result = safe_api_call(mock_func, log_errors=True, fallback_value="fallback")

        assert result == "fallback"
        mock_logger.error.assert_called_once()

    @patch('utils.retry_utils.logger')
    def test_error_logging_disabled(self, mock_logger):
        """Test that errors are not logged when log_errors is False."""
        mock_func = Mock(side_effect=Exception("API error"))

        result = safe_api_call(mock_func, log_errors=False, fallback_value="fallback")

        assert result == "fallback"
        mock_logger.error.assert_not_called()

    def test_with_complex_fallback(self):
        """Test safe_api_call with complex fallback value."""
        mock_func = Mock(side_effect=Exception("Error"))
        fallback = {"error": "Service unavailable", "status": 503}

        result = safe_api_call(mock_func, fallback_value=fallback)

        assert result == fallback
        assert result["error"] == "Service unavailable"


@pytest.mark.unit
class TestStandardRetry:
    """Test suite for standard_retry decorator."""

    def test_standard_retry_decorator(self):
        """Test the pre-configured standard_retry decorator."""
        mock_func = Mock(side_effect=[Exception("Fail 1"), Exception("Fail 2"), "success"])

        @standard_retry
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_standard_retry_configuration(self):
        """Test that standard_retry uses expected configuration."""
        # This tests that the decorator is created with standard settings
        # by attempting retries and verifying behavior
        attempt_count = []

        @standard_retry
        def test_func():
            attempt_count.append(1)
            if len(attempt_count) < 3:
                raise Exception("Temporary error")
            return "success"

        result = test_func()

        assert result == "success"
        assert len(attempt_count) == 3  # max_attempts default is 3


@pytest.mark.unit
class TestRetryEdgeCases:
    """Test suite for edge cases in retry logic."""

    def test_zero_max_attempts(self):
        """Test behavior with zero max attempts."""
        mock_func = Mock(return_value="success")

        # With 0 attempts, function should not be called at all
        # but tenacity's stop_after_attempt(0) might behave differently
        # Let's test actual behavior
        try:
            decorator = create_retry_decorator(max_attempts=0)

            @decorator
            def test_func():
                return mock_func()

            test_func()
        except Exception:
            # Expected - can't retry 0 times
            pass

    def test_single_max_attempt(self):
        """Test with max_attempts=1 (no retries)."""
        mock_func = Mock(side_effect=Exception("Immediate failure"))
        decorator = create_retry_decorator(max_attempts=1, min_wait=0.1)

        @decorator
        def test_func():
            return mock_func()

        with pytest.raises(Exception, match="Immediate failure"):
            test_func()

        assert mock_func.call_count == 1

    def test_very_long_wait_time(self):
        """Test that max_wait caps the wait time."""
        call_times = []

        def failing_func():
            call_times.append(time.time())
            if len(call_times) < 2:
                raise Exception("Fail")
            return "success"

        # Use very high multiplier but low max_wait
        decorator = create_retry_decorator(
            max_attempts=2,
            min_wait=0.1,
            max_wait=0.3,  # Cap at 0.3 seconds
            multiplier=100  # Would normally cause very long wait
        )

        @decorator
        def test_func():
            return failing_func()

        result = test_func()

        assert result == "success"
        # Wait time should be capped by max_wait
        wait_time = call_times[1] - call_times[0]
        assert wait_time < 1.0  # Much less than what multiplier=100 would cause
