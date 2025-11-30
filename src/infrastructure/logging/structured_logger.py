"""
Structured Logging for Midas Finance Bot
Provides JSON-formatted logs with context for better observability
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """
    Structured logger with JSON output and context management.
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Create JSON formatter
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s %(user_id)s %(command)s %(task_type)s %(duration)s %(error)s',
            rename_fields={
                'levelname': 'level',
                'name': 'logger'
            }
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler('logs/structured.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """
        Set context for all subsequent log messages.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context."""
        self.context = {}
    
    def _add_timestamp(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Add timestamp to extra fields."""
        extra['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        return extra
    
    def _merge_extra(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge context and extra fields."""
        merged = self.context.copy()
        if extra:
            merged.update(extra)
        return self._add_timestamp(merged)
    
    def info(self, message: str, **extra):
        """Log info message with context."""
        self.logger.info(message, extra=self._merge_extra(extra))
    
    def warning(self, message: str, **extra):
        """Log warning message with context."""
        self.logger.warning(message, extra=self._merge_extra(extra))
    
    def error(self, message: str, error: Optional[Exception] = None, **extra):
        """Log error message with context."""
        if error:
            extra['error'] = str(error)
            extra['error_type'] = type(error).__name__
        self.logger.error(message, extra=self._merge_extra(extra))
    
    def debug(self, message: str, **extra):
        """Log debug message with context."""
        self.logger.debug(message, extra=self._merge_extra(extra))
    
    def critical(self, message: str, **extra):
        """Log critical message with context."""
        self.logger.critical(message, extra=self._merge_extra(extra))
    
    # Convenience methods for common scenarios
    
    def log_bot_request(self, user_id: str, command: str, **extra):
        """Log bot request."""
        self.info(
            f"Bot request: {command}",
            user_id=user_id,
            command=command,
            **extra
        )
    
    def log_bot_error(self, user_id: str, command: str, error: Exception, **extra):
        """Log bot error."""
        self.error(
            f"Bot error in {command}",
            error=error,
            user_id=user_id,
            command=command,
            **extra
        )
    
    def log_ai_categorization(self, user_id: str, transaction_id: str, 
                             category: str, confidence: float, duration: float, **extra):
        """Log AI categorization."""
        self.info(
            f"AI categorization: {category}",
            user_id=user_id,
            transaction_id=transaction_id,
            category=category,
            confidence=confidence,
            duration=duration,
            **extra
        )
    
    def log_ai_correction(self, user_id: str, transaction_id: str,
                         ai_category: str, correct_category: str, **extra):
        """Log AI correction by user."""
        self.info(
            f"AI correction: {ai_category} → {correct_category}",
            user_id=user_id,
            transaction_id=transaction_id,
            ai_category=ai_category,
            correct_category=correct_category,
            **extra
        )
    
    def log_transaction_sync(self, user_id: str, wallet_id: str, 
                            count: int, duration: float, **extra):
        """Log transaction sync."""
        self.info(
            f"Synced {count} transactions",
            user_id=user_id,
            wallet_id=wallet_id,
            count=count,
            duration=duration,
            **extra
        )
    
    def log_queue_task(self, task_type: str, task_id: str, 
                      status: str, duration: Optional[float] = None, **extra):
        """Log queue task."""
        message = f"Queue task {status}: {task_type}"
        if duration:
            extra['duration'] = duration
        self.info(
            message,
            task_type=task_type,
            task_id=task_id,
            status=status,
            **extra
        )
    
    def log_db_query(self, table: str, operation: str, 
                    duration: float, rows_affected: Optional[int] = None, **extra):
        """Log database query."""
        message = f"DB {operation} on {table}"
        if rows_affected is not None:
            extra['rows_affected'] = rows_affected
        self.info(
            message,
            table=table,
            operation=operation,
            duration=duration,
            **extra
        )
    
    def log_redis_operation(self, operation: str, key: str, 
                           duration: float, status: str = "success", **extra):
        """Log Redis operation."""
        self.info(
            f"Redis {operation}: {key}",
            operation=operation,
            key=key,
            duration=duration,
            status=status,
            **extra
        )


# Global logger instances
bot_logger = StructuredLogger('midas.bot')
worker_logger = StructuredLogger('midas.worker')
db_logger = StructuredLogger('midas.db')
redis_logger = StructuredLogger('midas.redis')


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
