"""
Unit tests for retry logic.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from infrastructure.error_handling.retry import (
    RetryConfig,
    retry_async,
    with_retry,
    CircuitBreaker,
    CircuitBreakerOpenError
)


@pytest.mark.unit
@pytest.mark.error_handling
class TestRetryLogic:
    """Tests for retry logic."""
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry_async with successful function."""
        mock_func = AsyncMock(return_value="success")
        config = RetryConfig(max_attempts=3)
        
        result = await retry_async(mock_func, config)
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_async_failure_then_success(self):
        """Test retry_async with failure then success."""
        mock_func = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        result = await retry_async(mock_func, config)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_all_failures(self):
        """Test retry_async with all failures."""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        with pytest.raises(Exception, match="fail"):
            await retry_async(mock_func, config)
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        call_count = 0
        
        @with_retry(config=RetryConfig(max_attempts=3, initial_delay=0.01))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"
        
        result = await test_func()
        
        assert result == "success"
        assert call_count == 3


@pytest.mark.unit
@pytest.mark.error_handling
class TestCircuitBreaker:
    """Tests for Circuit Breaker."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        mock_func = AsyncMock(return_value="success")
        
        result = await cb.call(mock_func)
        
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        mock_func = AsyncMock(side_effect=Exception("fail"))
        
        # First 3 failures should open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(mock_func)
        
        assert cb.state == "OPEN"
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(mock_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self):
        """Test circuit breaker transitions to half-open."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        mock_func = AsyncMock(side_effect=Exception("fail"))
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(mock_func)
        
        assert cb.state == "OPEN"
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Next call should transition to half-open
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = await cb.call(mock_func)
        
        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
