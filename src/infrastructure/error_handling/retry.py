"""
Retry Logic с Exponential Backoff для external APIs.

Автоматически retry failed requests с умным backoff.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Optional, Type, Tuple
from functools import wraps
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """
    Configuration для retry logic.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Инициализация retry config.
        
        Args:
            max_attempts: Максимальное количество попыток
            initial_delay: Начальная задержка (секунды)
            max_delay: Максимальная задержка (секунды)
            exponential_base: База для exponential backoff
            jitter: Добавлять ли jitter (randomization)
            retryable_exceptions: Tuple of exceptions для retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Вычисляет delay для текущей попытки.
        
        Args:
            attempt: Номер попытки (0-indexed)
        
        Returns:
            Delay в секундах
        """
        # Exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Add jitter to avoid thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay


# Default configs для разных сценариев
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=60.0
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=2.0,
    max_delay=10.0
)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    **kwargs
) -> T:
    """
    Retry async function с exponential backoff.
    
    Args:
        func: Async function для retry
        *args: Positional arguments для func
        config: RetryConfig instance
        **kwargs: Keyword arguments для func
    
    Returns:
        Result of func
    
    Raises:
        Last exception if all retries failed
    """
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            
            return result
            
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} attempts failed. Last error: {e}"
                )
    
    # All retries failed
    raise last_exception


def with_retry(config: RetryConfig = DEFAULT_RETRY_CONFIG):
    """
    Decorator для automatic retry async functions.
    
    Usage:
        @with_retry(config=AGGRESSIVE_RETRY_CONFIG)
        async def fetch_blockchain_data(address: str):
            ...
    
    Args:
        config: RetryConfig instance
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        
        return wrapper
    
    return decorator


# Example usage:
"""
from .retry import with_retry, AGGRESSIVE_RETRY_CONFIG
from .exceptions import BlockchainAPIError

class BlockchainService:
    @with_retry(config=AGGRESSIVE_RETRY_CONFIG)
    async def fetch_balance(self, address: str) -> float:
        try:
            response = await self.api_client.get_balance(address)
            return response['balance']
        except Exception as e:
            raise BlockchainAPIError("Moralis", str(e))
"""


class CircuitBreaker:
    """
    Circuit Breaker pattern для external APIs.
    
    Предотвращает repeated calls к failing service.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Service is down, reject all requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Инициализация circuit breaker.
        
        Args:
            failure_threshold: Количество failures для открытия circuit
            recovery_timeout: Время до попытки recovery (секунды)
            expected_exception: Exception type для tracking
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(f"CircuitBreaker initialized: threshold={failure_threshold}")
    
    def _should_attempt_reset(self) -> bool:
        """Проверяет, нужно ли попробовать reset."""
        if self.state == "OPEN" and self.last_failure_time:
            import time
            return (time.time() - self.last_failure_time) >= self.recovery_timeout
        return False
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Вызывает function через circuit breaker.
        
        Args:
            func: Function для вызова
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of func
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            self.state = "HALF_OPEN"
            logger.info("Circuit breaker entering HALF_OPEN state")
        
        # Reject if circuit is open
        if self.state == "OPEN":
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Service unavailable. "
                f"Retry after {self.recovery_timeout}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                import time
                self.last_failure_time = time.time()
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )
            
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def with_circuit_breaker(breaker: CircuitBreaker):
    """
    Decorator для circuit breaker.
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=3)
        
        @with_circuit_breaker(breaker)
        async def fetch_data():
            ...
    
    Args:
        breaker: CircuitBreaker instance
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator
