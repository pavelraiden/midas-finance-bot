"""
Rate Limiting System
Prevents abuse by limiting the number of requests per user per time period
"""
import time
from typing import Dict, Callable
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
from src.infrastructure.logging.audit_logger import AuditLogger


class RateLimiter:
    """
    Token bucket rate limiter with per-user tracking.
    """
    
    def __init__(
        self,
        max_requests: int = 5,
        time_window: int = 60,
        cooldown_period: int = 300
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
            cooldown_period: Cooldown period in seconds after rate limit exceeded
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.cooldown_period = cooldown_period
        self.user_requests: Dict[int, list] = defaultdict(list)
        self.user_cooldowns: Dict[int, datetime] = {}
        self.audit_logger = AuditLogger()
    
    def is_rate_limited(self, user_id: int) -> bool:
        """
        Check if user is currently rate limited.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is rate limited, False otherwise
        """
        if user_id in self.user_cooldowns:
            cooldown_end = self.user_cooldowns[user_id]
            if datetime.now() < cooldown_end:
                return True
            else:
                del self.user_cooldowns[user_id]
        
        current_time = time.time()
        
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if current_time - t < self.time_window
        ]
        
        if len(self.user_requests[user_id]) >= self.max_requests:
            self.user_cooldowns[user_id] = datetime.now() + timedelta(seconds=self.cooldown_period)
            
            self.audit_logger.log_action(
                "rate_limiting",
                "limit_exceeded",
                {
                    "user_id": user_id,
                    "requests_count": len(self.user_requests[user_id]),
                    "cooldown_until": self.user_cooldowns[user_id].isoformat()
                }
            )
            
            return True
        
        return False
    
    def record_request(self, user_id: int):
        """
        Record a request for a user.
        
        Args:
            user_id: User ID making the request
        """
        self.user_requests[user_id].append(time.time())
    
    def get_remaining_requests(self, user_id: int) -> int:
        """
        Get number of remaining requests for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Number of remaining requests
        """
        current_time = time.time()
        
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if current_time - t < self.time_window
        ]
        
        return max(0, self.max_requests - len(self.user_requests[user_id]))
    
    def get_cooldown_remaining(self, user_id: int) -> int:
        """
        Get remaining cooldown time in seconds.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Remaining cooldown time in seconds, 0 if not in cooldown
        """
        if user_id not in self.user_cooldowns:
            return 0
        
        remaining = (self.user_cooldowns[user_id] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def reset_user(self, user_id: int):
        """
        Reset rate limiting for a user (admin function).
        
        Args:
            user_id: User ID to reset
        """
        if user_id in self.user_requests:
            del self.user_requests[user_id]
        if user_id in self.user_cooldowns:
            del self.user_cooldowns[user_id]
        
        self.audit_logger.log_action(
            "rate_limiting",
            "user_reset",
            {"user_id": user_id}
        )


rate_limiter_global = RateLimiter(max_requests=10, time_window=60)

rate_limiter_strict = RateLimiter(max_requests=3, time_window=60, cooldown_period=600)


def rate_limit(
    limiter: RateLimiter = rate_limiter_global,
    error_message: str = "Rate limit exceeded. Please try again later."
):
    """
    Decorator for rate limiting bot command handlers.
    
    Args:
        limiter: RateLimiter instance to use
        error_message: Message to send when rate limited
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            
            if limiter.is_rate_limited(user_id):
                cooldown = limiter.get_cooldown_remaining(user_id)
                await message.reply(
                    f"{error_message}\n"
                    f"Cooldown remaining: {cooldown} seconds"
                )
                return
            
            limiter.record_request(user_id)
            
            return await func(message, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit_sensitive(
    error_message: str = "Too many attempts. Please wait before trying again."
):
    """
    Strict rate limiting for sensitive operations.
    
    Args:
        error_message: Message to send when rate limited
        
    Returns:
        Decorated function
    """
    return rate_limit(limiter=rate_limiter_strict, error_message=error_message)
